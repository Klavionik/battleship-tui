from typing import Generator

from httpx import Auth, Request, Response


class IDTokenAuth(Auth):
    def __init__(self) -> None:
        self._id_token: str | None = None

    def auth_flow(self, request: Request) -> Generator[Request, Response, None]:
        if self._id_token:
            request.headers["Authorization"] = f"Bearer {self._id_token}"
        yield request

    def set_token(self, id_token: str) -> None:
        self._id_token = id_token

    def clear_token(self) -> None:
        self._id_token = None
