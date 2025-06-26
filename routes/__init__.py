from .auth import router as auth_router
from .users import router as users_router
from .departements import router as departements_router
from .demandes_conges import router as demandes_conges_router

__all__ = [
    "auth_router",
    "users_router", 
    "departements_router",
    "demandes_conges_router"
] 