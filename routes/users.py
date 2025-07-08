import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.database import get_database
from models.user import User, UserRead, UserUpdate, RoleEnum
from models.demande_conge import DemandeConge
from utils.auth import fastapi_users
from utils.dependencies import get_current_user, require_drh, require_manager

router = APIRouter(prefix="/users", tags=["users"])

async def enrich_user_with_solde_restant(db: AsyncSession, user: User) -> UserRead:
    """Enrichit un utilisateur avec le calcul du solde de congés restant"""
    
    # Récupérer les demandes de l'utilisateur
    demandes_result = await db.execute(
        select(DemandeConge).where(DemandeConge.demandeur_id == user.id)
    )
    demandes = demandes_result.scalars().all()
    
    # Calculer le solde restant
    solde_restant = user.calculate_solde_conges_restant(demandes)
    
    # Créer le UserRead avec le solde restant
    user_data = UserRead(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        nom=user.nom,
        prenom=user.prenom,
        telephone=user.telephone,
        numero_piece_identite=user.numero_piece_identite,
        poste=user.poste,
        role=user.role,
        date_embauche=user.date_embauche,
        solde_conges=user.solde_conges,
        solde_conges_restant=solde_restant,
        departement_id=user.departement_id,
        nom_complet=user.nom_complet,
        date_naissance=user.date_naissance,
        nombre_enfants=user.nombre_enfants,
        has_medaille_honneur=user.has_medaille_honneur,
        genre=user.genre
    )
    
    return user_data

async def enrich_users_with_solde_restant(db: AsyncSession, users: List[User]) -> List[UserRead]:
    """Enrichit une liste d'utilisateurs avec le calcul du solde de congés restant"""
    enriched_users = []
    for user in users:
        enriched_user = await enrich_user_with_solde_restant(db, user)
        enriched_users.append(enriched_user)
    return enriched_users

# Routes CRUD des utilisateurs (FastAPIUsers par défaut)
# IMPORTANT: Inclure nos routes personnalisées AVANT FastAPIUsers pour éviter les conflits
# FastAPIUsers génère des routes comme /{user_id} qui peuvent masquer nos routes personnalisées

@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère le profil de l'utilisateur connecté"""
    return await enrich_user_with_solde_restant(db, current_user)

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
    return await enrich_users_with_solde_restant(db, users)

@router.get("", response_model=List[UserRead])
async def get_all_users(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère tous les utilisateurs selon le rôle :
    - DRH : tous les employés et chefs de service (pour la gestion globale)
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
    return await enrich_users_with_solde_restant(db, users)

@router.get("/equipe", response_model=List[UserRead])
async def get_my_team(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère l'équipe selon le rôle de l'utilisateur connecté
    - DRH : employés de son département (Direction des Ressources Humaines)
    - Chef de service : employés de son département
    - Employé : accès refusé
    """
    if current_user.role == RoleEnum.EMPLOYE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les employés ne peuvent pas accéder à cette route"
        )
    
    # Pour DRH et Chef de service : récupérer les employés de leur département
    if not current_user.departement_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utilisateur sans département assigné"
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
    return await enrich_users_with_solde_restant(db, users)

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
    return await enrich_users_with_solde_restant(db, managers)

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
    return await enrich_user_with_solde_restant(db, user)

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
    return await enrich_user_with_solde_restant(db, user)

# Routes CRUD des utilisateurs (FastAPIUsers par défaut) - À la fin pour éviter les conflits
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
)