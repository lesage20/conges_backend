import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.database import get_database
from models.user import User, UserRead, UserUpdate, RoleEnum
from utils.auth import fastapi_users
from utils.dependencies import get_current_user, require_drh, require_manager

router = APIRouter(prefix="/users", tags=["users"])

# Routes CRUD des utilisateurs (FastAPIUsers par défaut)
# IMPORTANT: Inclure nos routes personnalisées AVANT FastAPIUsers pour éviter les conflits
# FastAPIUsers génère des routes comme /{user_id} qui peuvent masquer nos routes personnalisées

@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Récupère le profil de l'utilisateur connecté"""
    return current_user

@router.get("/departement/{departement_id}", response_model=List[UserRead])
async def get_users_by_departement(
    departement_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_manager())
):
    """Récupère tous les utilisateurs d'un département (Manager/DRH uniquement)"""
    result = await db.execute(
        select(User)
        .where(User.departement_id == departement_id)
        .options(selectinload(User.departement))
    )
    users = result.scalars().all()
    return users

@router.get("/tous", response_model=List[UserRead])
async def get_all_users(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère tous les utilisateurs selon le rôle :
    - DRH : tous les employés et chefs de service  
    - Chef de service : tous les employés de son département
    - Employé : accès refusé
    """
    if current_user.role == RoleEnum.EMPLOYE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les employés ne peuvent pas accéder à cette route"
        )
    
    if current_user.role == RoleEnum.DRH:
        # DRH : récupérer tous les employés et chefs de service (sauf DRH)
        result = await db.execute(
            select(User)
            .where(
                User.role.in_([RoleEnum.EMPLOYE, RoleEnum.CHEF_SERVICE])
            )
            .options(selectinload(User.departement))
        )
    elif current_user.role == RoleEnum.CHEF_SERVICE:
        # Chef de service : récupérer tous les employés de son département
        if not current_user.departement_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chef de service sans département assigné"
            )
        
        result = await db.execute(
            select(User)
            .where(
                User.departement_id == current_user.departement_id,
                User.role == RoleEnum.EMPLOYE
            )
            .options(selectinload(User.departement))
        )
    
    users = result.scalars().all()
    return users

@router.get("/equipe", response_model=List[UserRead])
async def get_my_team(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Alias pour /tous - utilisé pour la page "Mon Équipe"
    Récupère l'équipe selon le rôle de l'utilisateur connecté
    """
    return await get_all_users(db, current_user)

@router.get("/managers", response_model=List[UserRead])
async def get_managers(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_drh())
):
    """Récupère tous les managers (DRH uniquement)"""
    result = await db.execute(
        select(User)
        .where(User.role.in_([RoleEnum.CHEF_SERVICE, RoleEnum.DRH]))
        .options(selectinload(User.departement))
    )
    managers = result.scalars().all()
    return managers

@router.put("/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: uuid.UUID,
    new_role: RoleEnum,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_drh())
):
    """Met à jour le rôle d'un utilisateur (DRH uniquement)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    user.role = new_role
    await db.commit()
    await db.refresh(user)
    return user

@router.put("/{user_id}/departement", response_model=UserRead)
async def assign_departement(
    user_id: uuid.UUID,
    departement_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_drh())
):
    """Assigne un utilisateur à un département (DRH uniquement)"""
    # Vérifier que l'utilisateur existe
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Vérifier que le département existe
    from models.departement import Departement
    result = await db.execute(select(Departement).where(Departement.id == departement_id))
    departement = result.scalar_one_or_none()
    
    if not departement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Département non trouvé"
        )
    
    user.departement_id = departement_id
    await db.commit()
    await db.refresh(user)
    return user 

# Routes CRUD des utilisateurs (FastAPIUsers par défaut) - À la fin pour éviter les conflits
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
)