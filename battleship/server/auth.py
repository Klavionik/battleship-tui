import asyncio
import enum
from abc import ABC, abstractmethod
from secrets import token_urlsafe
from typing import Any, cast

import jwt
from auth0.authentication import Database, GetToken  # type: ignore[import]
from auth0.management import Auth0  # type: ignore[import]

from battleship.server.config import Config
from battleship.shared.models import IDToken, LoginData


class UserRole(enum.StrEnum):
    GUEST = "guest"
    USER = "user"


class AuthManager(ABC):
    @abstractmethod
    async def login_guest(self) -> LoginData:
        pass

    @abstractmethod
    async def login(self, username: str, password: str) -> LoginData:
        pass

    @abstractmethod
    async def signup(self, email: str, password: str, nickname: str) -> None:
        pass

    @abstractmethod
    async def refresh_id_token(self, refresh_token: str) -> IDToken:
        pass


class Auth0AuthManager(AuthManager):
    def __init__(self, config: Config):
        self.domain = config.AUTH0_DOMAIN
        self.client_id = config.AUTH0_CLIENT_ID
        self.client_secret = config.AUTH0_CLIENT_SECRET
        self.audience = config.auth0_audience
        self.realm = config.AUTH0_REALM

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

        self.mgmt = Auth0(self.domain, self._fetch_management_token(self.audience))
        self.roles: dict[UserRole, str] = self._fetch_roles()

    async def login_guest(self) -> LoginData:
        return await self.signup_anonymously()

    async def login(self, username: str, password: str) -> LoginData:
        def _login() -> Any:
            return self.gettoken.login(
                username, password, realm=self.realm, scope="openid offline_access"
            )

        tokens = await asyncio.to_thread(_login)
        id_token = tokens["id_token"]
        payload = _read_token(id_token)

        return LoginData.from_dict(
            dict(
                id_token=tokens["id_token"],
                refresh_token=tokens["refresh_token"],
                nickname=payload["nickname"],
                expires_in=payload["exp"],
            )
        )

    async def signup(self, email: str, password: str, nickname: str) -> None:
        def _signup() -> dict[str, Any]:
            response = self.database.signup(
                email=email,
                username=nickname,
                password=password,
                nickname=nickname,
                connection=self.realm,
            )

            return cast(dict[str, Any], response)

        data = await asyncio.to_thread(_signup)
        await self.assign_role(data["_id"], UserRole.USER)

    async def refresh_id_token(self, refresh_token: str) -> IDToken:
        def _refresh_id_token() -> dict[str, Any]:
            response = self.gettoken.refresh_token(refresh_token)

            return cast(dict[str, Any], response)

        data = await asyncio.to_thread(_refresh_id_token)
        id_token = data["id_token"]
        payload = _read_token(id_token)
        return IDToken(id_token=id_token, expires_at=payload["exp"])

    async def assign_role(self, user_id: str, role: UserRole) -> None:
        role_id = self.roles[role]
        sub_prefix = "auth0|"

        if not user_id.startswith(sub_prefix):
            user_id = sub_prefix + user_id

        def _assign_roles() -> None:
            self.mgmt.users.add_roles(user_id, [role_id])

        await asyncio.to_thread(_assign_roles)

    async def signup_anonymously(self) -> LoginData:
        nickname = _make_random_nickname()
        password = _make_random_password()

        def _signup() -> dict[str, Any]:
            response = self.database.signup(
                email=f"{nickname}@battleship.invalid",
                password=password,
                username=nickname,
                nickname=nickname,
                connection=self.realm,
            )

            return cast(dict[str, Any], response)

        data = await asyncio.to_thread(_signup)
        await self.assign_role(data["_id"], UserRole.GUEST)
        tokens = self.gettoken.login(nickname, password, realm=self.realm, scope="openid")

        return LoginData(id_token=tokens["id_token"], nickname=nickname)

    def _fetch_management_token(self, audience: str) -> str:
        data = self.gettoken.client_credentials(audience)
        return cast(str, data["access_token"])

    def _fetch_roles(self) -> dict[UserRole, str]:
        data = self.mgmt.roles.list()
        return {role["name"]: role["id"] for role in data["roles"]}


def _make_random_nickname() -> str:
    return f"Guest_{token_urlsafe(6)}"


def _make_random_password() -> str:
    return token_urlsafe(6)


def _read_token(token: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jwt.decode(token, algorithms=["RS256"], options=dict(verify_signature=False)),
    )
