import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase

from models.user import User, UserCreate
from models.database import get_user_db

SECRET = "SECRET_KEY_CHANGE_IN_PRODUCTION"  # À changer en production

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"Utilisateur {user.id} s'est inscrit.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Utilisateur {user.id} a oublié son mot de passe. Token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Vérification demandée pour l'utilisateur {user.id}. Token: {token}")

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

# Configuration de l'authentification JWT
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# Instance FastAPIUsers
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Dépendances d'authentification
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True) 