from fastapi import APIRouter

from models.user import UserRead, UserCreate
from utils.auth import auth_backend, fastapi_users

router = APIRouter()

# Routes d'authentification
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# Routes d'inscription
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# Routes de réinitialisation de mot de passe
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

# Routes de vérification
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
) 