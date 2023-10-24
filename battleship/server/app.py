from blacksheep import Application
from blacksheep.server.authentication.jwt import JWTBearerAuthentication
from blacksheep.server.authorization import Policy
from guardpost.common import AuthenticatedRequirement

from battleship.server.auth import AuthManager, FirebaseAuthManager
from battleship.server.config import Config, get_config
from battleship.server.connections import ConnectionManager
from battleship.server.routes import router
from battleship.server.sessions import Sessions


def create_app() -> Application:
    config = get_config()
    app = Application(router=router)

    app.services.add_instance(config, Config)
    app.services.add_singleton(AuthManager, FirebaseAuthManager)
    app.services.add_singleton(Sessions)
    app.services.add_singleton(ConnectionManager)

    app.use_authentication().add(
        JWTBearerAuthentication(
            keys_url=config.FIREBASE_JWKS_URL,
            valid_audiences=[config.FIREBASE_PROJECT_ID],
            valid_issuers=[config.FIREBASE_TOKEN_ISSUER],
        )
    )

    app.use_authorization().with_default_policy(
        Policy("authenticated", AuthenticatedRequirement()),
    )
    return app
