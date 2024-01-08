import asyncio
from abc import ABC, abstractmethod
from enum import auto
from functools import partial
from random import choice
from secrets import token_urlsafe
from string import ascii_letters, digits
from typing import Any, TypeAlias, cast

import auth0  # type: ignore[import-untyped]
import jwt
from auth0.authentication import Database, GetToken  # type: ignore[import-untyped]
from auth0.management import Auth0 as _Auth0  # type: ignore[import-untyped]
from loguru import logger

from battleship.server.config import Config
from battleship.shared.compat import StrEnum
from battleship.shared.models import IDToken, LoginData


class UserRole(StrEnum):
    GUEST = auto()
    USER = auto()


JSONPayload: TypeAlias = dict[str, Any]


class AuthError(Exception):
    pass


class WrongCredentials(AuthError):
    pass


class InvalidSignup(AuthError):
    pass


class AuthManager(ABC):
    @abstractmethod
    async def login_guest(self) -> LoginData:
        pass

    @abstractmethod
    async def login(self, nickname: str, password: str) -> LoginData:
        pass

    @abstractmethod
    async def signup(self, email: str, password: str, nickname: str) -> None:
        pass

    @abstractmethod
    async def refresh_id_token(self, refresh_token: str) -> IDToken:
        pass


class Auth0AuthManager(AuthManager):
    def __init__(self, config: Config):
        self.api = Auth0API.from_config(config)
        self.roles: dict[str, str] = config.AUTH0_ROLES

    async def login_guest(self) -> LoginData:
        nickname = _make_random_nickname()
        password = _make_random_password()
        email = f"{nickname}@battleship.invalid"

        data = await self.api.signup(email, nickname, password)
        await self.assign_role(data["_id"], UserRole.GUEST)
        tokens = await self.api.login(nickname, password)
        id_token = tokens["id_token"]
        payload = _read_token(id_token)
        return LoginData(
            user_id=payload["sub"],
            id_token=tokens["id_token"],
            refresh_token=tokens["refresh_token"],
            nickname=nickname,
            expires_at=payload["exp"],
        )

    async def login(self, nickname: str, password: str) -> LoginData:
        try:
            tokens = await self.api.login(nickname, password)
        except auth0.Auth0Error as exc:
            raise WrongCredentials(str(exc))

        id_token = tokens["id_token"]
        payload = _read_token(id_token)

        return LoginData(
            user_id=payload["sub"],
            id_token=tokens["id_token"],
            refresh_token=tokens["refresh_token"],
            nickname=payload["nickname"],
            expires_at=payload["exp"],
        )

    async def signup(self, email: str, password: str, nickname: str) -> None:
        try:
            data = await self.api.signup(email, nickname, password)
            await self.assign_role(data["_id"], UserRole.USER)
        except auth0.Auth0Error as exc:
            logger.error(f"Error during signup: {exc.error_code=} {exc.message=}")
            raise InvalidSignup("Cannot create such account.")

    async def refresh_id_token(self, refresh_token: str) -> IDToken:
        data = await self.api.refresh_token(refresh_token)
        id_token = data["id_token"]
        payload = _read_token(id_token)
        return IDToken(id_token=id_token, expires_at=payload["exp"])

    async def assign_role(self, user_id: str, role: UserRole) -> None:
        role_id = self.roles[role]
        sub_prefix = "auth0|"

        if not user_id.startswith(sub_prefix):
            user_id = sub_prefix + user_id

        await self.api.add_roles(user_id, role_id)


class Auth0API:
    def __init__(self, domain: str, client_id: str, client_secret: str, realm: str, audience: str):
        self.domain = domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.audience = audience
        self.realm = realm

        self.database = Database(
            self.domain,
            self.client_id,
            self.client_secret,
        )
        self.gettoken = GetToken(
            self.domain,
            self.client_id,
            self.client_secret,
        )
        self._mgmt: _Auth0 | None = None

    @classmethod
    def from_config(cls, config: Config) -> "Auth0API":
        return cls(
            config.AUTH0_DOMAIN,
            config.AUTH0_CLIENT_ID,
            config.AUTH0_CLIENT_SECRET,
            config.AUTH0_REALM,
            config.auth0_audience,
        )

    @property
    def mgmt(self) -> _Auth0:
        if self._mgmt is None:
            self._mgmt = _Auth0(self.domain, self._fetch_management_token(self.audience))
        return self._mgmt

    async def add_roles(self, user_id: str, *roles: str) -> JSONPayload:
        func = partial(self.mgmt.users.add_roles, id=user_id, roles=roles)
        data = await asyncio.to_thread(func)
        return cast(JSONPayload, data)

    async def signup(self, email: str, nickname: str, password: str) -> JSONPayload:
        func = partial(
            self.database.signup,
            email=email,
            username=nickname,
            password=password,
            nickname=nickname,
            connection=self.realm,
        )
        data = await asyncio.to_thread(func)
        return cast(JSONPayload, data)

    async def login(
        self, username: str, password: str, scope: str = "openid offline_access"
    ) -> JSONPayload:
        func = partial(self.gettoken.login, username, password, scope=scope, realm=self.realm)
        data = await asyncio.to_thread(func)
        return cast(JSONPayload, data)

    async def delete_user(self, user_id: str) -> JSONPayload:
        func = partial(self.mgmt.users.delete, id=user_id)
        data = await asyncio.to_thread(func)
        return cast(JSONPayload, data)

    async def refresh_token(self, refresh_token: str) -> JSONPayload:
        func = partial(self.gettoken.refresh_token, refresh_token=refresh_token)
        data = await asyncio.to_thread(func)
        return cast(JSONPayload, data)

    def _fetch_management_token(self, audience: str) -> str:
        data = self.gettoken.client_credentials(audience)
        return cast(str, data["access_token"])


def _make_random_nickname(postfix_length: int = 7) -> str:
    def _make_postfix() -> str:
        namespace = ascii_letters + digits
        return "".join(choice(namespace) for _ in range(postfix_length))

    return f"Guest_{_make_postfix()}"


def _make_random_password() -> str:
    return token_urlsafe(12)


def _read_token(token: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jwt.decode(token, algorithms=["RS256"], options=dict(verify_signature=False)),
    )
