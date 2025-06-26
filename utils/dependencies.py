from typing import List
from fastapi import Depends, HTTPException, status

from models.user import User, RoleEnum
from models.database import get_user_db
from .auth import current_active_user

async def get_current_user(user: User = Depends(current_active_user)) -> User:
    """Récupère l'utilisateur actuel connecté"""
    return user

def require_role(required_role: RoleEnum):
    """Décorateur de dépendance pour vérifier qu'un utilisateur a le rôle requis"""
    async def check_role(user: User = Depends(current_active_user)) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle {required_role.value} requis"
            )
        return user
    return check_role

def require_roles(required_roles: List[RoleEnum]):
    """Décorateur de dépendance pour vérifier qu'un utilisateur a l'un des rôles requis"""
    async def check_roles(user: User = Depends(current_active_user)) -> User:
        if user.role not in required_roles:
            roles_str = ", ".join([role.value for role in required_roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"L'un des rôles suivants est requis: {roles_str}"
            )
        return user
    return check_roles

def require_drh():
    """Décorateur pour les endpoints nécessitant le rôle DRH"""
    return require_role(RoleEnum.DRH)

def require_manager():
    """Décorateur pour les endpoints nécessitant le rôle chef de service ou DRH"""
    return require_roles([RoleEnum.CHEF_SERVICE, RoleEnum.DRH])

def require_admin():
    """Décorateur pour les endpoints nécessitant les droits admin (superuser ou DRH)"""
    async def check_admin(user: User = Depends(current_active_user)) -> User:
        if not user.is_superuser and user.role != RoleEnum.DRH:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits administrateur requis"
            )
        return user
    return check_admin 