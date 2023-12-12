from contextvars import ContextVar

client_version: ContextVar[str] = ContextVar("client_version")
