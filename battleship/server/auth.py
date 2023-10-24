from abc import ABC, abstractmethod
from secrets import token_urlsafe
from typing import cast

from blacksheep import FromHeader
from httpx import AsyncClient

from battleship.server.config import Config
from battleship.shared.models import LoginData


class AuthError(Exception):
    pass


class UserVerificationFailed(AuthError):
    pass


class TokenHeader(FromHeader[str]):
    name = "id_token"


class AuthManager(ABC):
    @abstractmethod
    async def login_guest(self) -> LoginData:
        pass


class FirebaseAuthManager(AuthManager):
    identity_url = "https://identitytoolkit.googleapis.com/v1/"
    token_url = "https://securetoken.googleapis.com/v1/"

    def __init__(self, config: Config):
        self.project_id = config.FIREBASE_PROJECT_ID
        self.api_key = config.FIREBASE_WEB_API_KEY
        self.client = AsyncClient
        self.key_param = dict(key=self.api_key)

    async def login_guest(self) -> LoginData:
        return await self.sign_in_anonymously()

    async def sign_in_anonymously(self) -> LoginData:
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
        return LoginData.model_validate(
            dict(id_token=id_token, user={"display_name": display_name, "guest": True})
        )

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


def _make_random_handle() -> str:
    return f"Guest_{token_urlsafe(6)}"
