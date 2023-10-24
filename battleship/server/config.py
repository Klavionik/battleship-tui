from pydantic_settings import BaseSettings


class Config(BaseSettings):
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_WEB_API_KEY: str = ""
    FIREBASE_JWKS_URL: str = ""
    FIREBASE_TOKEN_ISSUER: str = ""


def get_config() -> Config:
    return Config()
