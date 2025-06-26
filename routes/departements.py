import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.database import get_database
from models.departement import Departement, DepartementRead, DepartementCreate, DepartementUpdate
from models.user import User, RoleEnum
from utils.dependencies import get_current_user, require_drh

router = APIRouter(prefix="/departements", tags=["departements"])

@router.get("/", response_model=List[DepartementRead])
async def get_departements(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère tous les départements"""
    result = await db.execute(
        select(Departement)
        .options(selectinload(Departement.employes))
    )
    departements = result.scalars().all()
    return departements

@router.get("/{departement_id}", response_model=DepartementRead)
async def get_departement(
    departement_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère un département par son ID"""
    result = await db.execute(
        select(Departement)
        .where(Departement.id == departement_id)
        .options(selectinload(Departement.employes))
    )
    departement = result.scalar_one_or_none()
    
    if not departement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Département non trouvé"
        )
    
    return departement

@router.post("/", response_model=DepartementRead)
async def create_departement(
    departement_data: DepartementCreate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_drh())
):
    """Crée un nouveau département (DRH uniquement)"""
    departement = Departement(**departement_data.dict())
    db.add(departement)
    await db.commit()
    await db.refresh(departement)
    return departement

@router.put("/{departement_id}", response_model=DepartementRead)
async def update_departement(
    departement_id: uuid.UUID,
    departement_data: DepartementUpdate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_drh())
):
    """Met à jour un département (DRH uniquement)"""
    result = await db.execute(
        select(Departement).where(Departement.id == departement_id)
    )
    departement = result.scalar_one_or_none()
    
    if not departement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Département non trouvé"
        )
    
    update_data = departement_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(departement, field, value)
    
    await db.commit()
    await db.refresh(departement)
    return departement

@router.delete("/{departement_id}")
async def delete_departement(
    departement_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_drh())
):
    """Supprime un département (DRH uniquement)"""
    result = await db.execute(
        select(Departement).where(Departement.id == departement_id)
    )
    departement = result.scalar_one_or_none()
    
    if not departement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Département non trouvé"
        )
    
    # Vérifier qu'il n'y a pas d'employés dans ce département
    result = await db.execute(
        select(User).where(User.departement_id == departement_id)
    )
    employes = result.scalars().all()
    
    if employes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer un département contenant des employés"
        )
    
    await db.delete(departement)
    await db.commit()
    return {"message": "Département supprimé avec succès"}

@router.put("/{departement_id}/chef", response_model=DepartementRead)
async def assign_chef_departement(
    departement_id: uuid.UUID,
    chef_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_drh())
):
    """Assigne un chef de département (DRH uniquement)"""
    # Vérifier que le département existe
    result = await db.execute(
        select(Departement).where(Departement.id == departement_id)
    )
    departement = result.scalar_one_or_none()
    
    if not departement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Département non trouvé"
        )
    
    # Vérifier que l'utilisateur existe et a le bon rôle
    result = await db.execute(select(User).where(User.id == chef_id))
    chef = result.scalar_one_or_none()
    
    if not chef:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    if chef.role != RoleEnum.CHEF_SERVICE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'utilisateur doit avoir le rôle 'chef_service'"
        )
    
    # Assigner le chef et affecter l'utilisateur au département
    departement.chef_departement_id = chef_id
    chef.departement_id = departement_id
    
    await db.commit()
    await db.refresh(departement)
    return departement

@router.get("/{departement_id}/stats")
async def get_departement_stats(
    departement_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère les statistiques d'un département"""
    result = await db.execute(
        select(Departement)
        .where(Departement.id == departement_id)
        .options(selectinload(Departement.employes))
    )
    departement = result.scalar_one_or_none()
    
    if not departement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Département non trouvé"
        )
    
    total_employes = len(departement.employes)
    total_managers = len([emp for emp in departement.employes if emp.role in ["chef_service", "drh"]])
    
    return {
        "departement_id": departement_id,
        "nom": departement.nom,
        "total_employes": total_employes,
        "total_managers": total_managers,
        "budget_conges": departement.budget_conges,
        "employes": [
            {
                "id": emp.id,
                "nom_complet": emp.nom_complet,
                "poste": emp.poste,
                "role": emp.role
            }
            for emp in departement.employes
        ]
    } 