import asyncio
from abc import ABC, abstractmethod
from secrets import token_urlsafe
from typing import Any, cast

import jwt
from httpx import AsyncClient
from jwt import PyJWKClient

from battleship.server.config import Config
from battleship.server.schemas import GuestUser


class AuthManager(ABC):
    @abstractmethod
    async def login_guest(self) -> GuestUser:
        pass

    @abstractmethod
    async def verify_user(self, token: str) -> None:
        pass


class FirebaseAuthManager(AuthManager):
    identity_url = "https://identitytoolkit.googleapis.com/v1/"
    token_url = "https://securetoken.googleapis.com/v1/"
    jwks_url = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"  # noqa

    def __init__(self, config: Config):
        self.project_id = config.FIREBASE_PROJECT_ID
        self.api_key = config.FIREBASE_WEB_API_KEY
        self.client = AsyncClient
        self.jwk_client = PyJWKClient(self.jwks_url)
        self.key_param = dict(key=self.api_key)

    async def login_guest(self) -> GuestUser:
        return await self.sign_in_anonymously()

    async def verify_user(self, token: str) -> None:
        await self.verify_id_token(token)

    async def sign_in_anonymously(self) -> GuestUser:
        async with self.client(base_url=self.identity_url) as client:
            response = await client.post(
                "/accounts:signUp", params=self.key_param, json=dict(returnSecureToken=True)
            )
            data = response.json()
            id_token, refresh_token = data["idToken"], data["refreshToken"]

            display_name = _make_random_handle()
            response = await client.post(
                "/accounts:update",
                params=self.key_param,
                json=dict(returnSecureToken=True, idToken=id_token, displayName=display_name),
            )
            data = response.json()

            assert data["displayName"] == display_name

            id_token = await self.refresh_id_token(refresh_token)

        return GuestUser(display_name=display_name, access_token=id_token)

    async def refresh_id_token(self, refresh_token: str) -> str:
        async with self.client(base_url=self.token_url) as client:
            response = await client.post(
                "/token",
                params=self.key_param,
                json=dict(grant_type="refresh_token", refresh_token=refresh_token),
            )
            data = response.json()
            new_id_token = data["id_token"]
            return cast(str, new_id_token)

    async def verify_id_token(self, id_token: str) -> dict[str, Any]:
        signing_key = await asyncio.to_thread(
            self.jwk_client.get_signing_key_from_jwt, token=id_token
        )
        payload = jwt.decode(
            id_token, signing_key.key, algorithms=["RS256"], audience=self.project_id
        )
        return cast(dict[str, Any], payload)


def _make_random_handle() -> str:
    return f"Guest_{token_urlsafe(6)}"
