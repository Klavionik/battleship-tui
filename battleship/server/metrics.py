from typing import Any

from aioprometheus.asgi.middleware import EXCLUDE_PATHS
from aioprometheus.asgi.middleware import MetricsMiddleware as _MetricsMiddleware
from aioprometheus.asgi.middleware import Receive, Scope, Send
from aioprometheus.collectors import REGISTRY, Counter, Gauge
from aioprometheus.renderer import render
from blacksheep import Request, Router
from guardpost import AuthenticationHandler, Identity

websocket_connections = Gauge(
    "websocket_connections",
    doc="Active WebSocket connections",
)
websocket_messages_in = Counter(
    "websocket_messages_in_total",
    doc="Inbound WebSocket messages amount",
)
websocket_messages_out = Counter(
    "websocket_messages_out_total",
    doc="Outbound WebSocket messages amount",
)
games_started_total = Counter(
    "games_started_total",
    doc="Started games amount",
)
games_finished_total = Counter(
    "games_finished_total",
    doc="Finished games amount",
)
games_cancelled_total = Counter(
    "games_cancelled_total",
    doc="Cancelled games amount",
)
games_now = Gauge(
    "games_now",
    doc="Amount of games in-progress",
)


class MetricsScraperAuthenticationHandler(AuthenticationHandler):
    def __init__(self, scraper_secret: str):
        self._secret = scraper_secret.encode()

    def authenticate(self, context: Request) -> Identity | None:
        header_value = context.get_first_header(b"Authorization")

        try:
            type_, secret = header_value.split()  # type: ignore[union-attr]
        except Exception:
            context.identity = None
        else:
            if type_ == b"Bearer" and secret == self._secret:
                context.identity = Identity({"id": "scraper"}, authentication_mode="Bearer")
            else:
                context.identity = None

        return context.identity


class MetricsMiddleware(_MetricsMiddleware):
    """
    ioprometheus.MetricsMiddleware that doesn't fail on WebSocket connections
    and extracts template paths from Blacksheep.
    """

    def __init__(self, *args: Any, router: Router, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.router = router
        self.exclude_paths = EXCLUDE_PATHS + ("/healthz",)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await self.asgi_callable(scope, receive, send)
            return

        await super().__call__(scope, receive, send)

    def get_full_or_template_path(self, scope: Scope) -> str:
        root_path = scope.get("root_path", "")
        path = scope.get("path", "")
        full_path = f"{root_path}{path}"
        method = scope.get("method", "").upper()

        if self.use_template_urls:
            match = self.router.get_match_by_method_and_path(method, path)

            if match is not None:
                return match.pattern.decode()
        return full_path


def render_metrics(accept_headers: list[bytes]) -> tuple[str, dict[bytes, bytes]]:
    accept_headers_decoded = [value.decode() for value in accept_headers]
    content, headers = render(REGISTRY, accept_headers_decoded)
    headers = {k.encode(): v.encode() for k, v in headers.items()}
    return content.decode(), headers
