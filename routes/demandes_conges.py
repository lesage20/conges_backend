import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from models.database import get_database
from models.demande_conge import (
    DemandeConge, DemandeCongeRead, DemandeCongeCreate, DemandeCongeUpdate, 
    DemandeCongeValidation, StatutDemandeEnum, TypeCongeEnum
)
from models.user import User, RoleEnum
from utils.dependencies import get_current_user, require_manager

router = APIRouter(prefix="/demandes-conges", tags=["demandes-conges"])

@router.get("/", response_model=List[DemandeCongeRead])
async def get_demandes_conges(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
    statut: Optional[StatutDemandeEnum] = Query(None),
    type_conge: Optional[TypeCongeEnum] = Query(None),
    limit: int = Query(50, le=100)
):
    """Récupère les demandes de congés selon le rôle de l'utilisateur"""
    query = select(DemandeConge).options(
        selectinload(DemandeConge.demandeur),
        selectinload(DemandeConge.valideur)
    )
    
    # Filtrer selon le rôle
    if current_user.role == RoleEnum.EMPLOYE:
        query = query.where(DemandeConge.demandeur_id == current_user.id)
    elif current_user.role == RoleEnum.CHEF_SERVICE:
        # Le chef de service voit ses demandes + celles de son département
        query = query.where(
            or_(
                DemandeConge.demandeur_id == current_user.id,
                DemandeConge.demandeur_id.in_(
                    select(User.id).where(
                        and_(
                            User.departement_id == current_user.departement_id,
                            User.role == RoleEnum.EMPLOYE
                        )
                    )
                )
            )
        )
    
    # Filtres optionnels
    if statut:
        query = query.where(DemandeConge.statut == statut)
    if type_conge:
        query = query.where(DemandeConge.type_conge == type_conge)
    
    query = query.limit(limit).order_by(DemandeConge.date_demande.desc())
    
    result = await db.execute(query)
    demandes = result.scalars().all()
    return demandes

@router.get("/mes-demandes", response_model=List[DemandeCongeRead])
async def get_my_demandes(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère les demandes de l'utilisateur connecté"""
    result = await db.execute(
        select(DemandeConge)
        .where(DemandeConge.demandeur_id == current_user.id)
        .options(
            selectinload(DemandeConge.demandeur),
            selectinload(DemandeConge.valideur)
        )
        .order_by(DemandeConge.date_demande.desc())
    )
    demandes = result.scalars().all()
    return demandes

@router.get("/en-attente", response_model=List[DemandeCongeRead])
async def get_pending_demandes(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_manager())
):
    """Récupère les demandes en attente de validation (Manager/DRH uniquement)"""
    query = select(DemandeConge).where(
        DemandeConge.statut == StatutDemandeEnum.EN_ATTENTE
    ).options(
        selectinload(DemandeConge.demandeur),
        selectinload(DemandeConge.valideur)
    )
    
    if current_user.role == RoleEnum.CHEF_SERVICE:
        # Chef de service : seulement les demandes de son département (employés)
        query = query.where(
            DemandeConge.demandeur_id.in_(
                select(User.id).where(
                    and_(
                        User.departement_id == current_user.departement_id,
                        User.role == RoleEnum.EMPLOYE
                    )
                )
            )
        )
    
    result = await db.execute(query.order_by(DemandeConge.date_demande.asc()))
    demandes = result.scalars().all()
    return demandes

@router.get("/{demande_id}", response_model=DemandeCongeRead)
async def get_demande_conge(
    demande_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère une demande de congé par son ID"""
    result = await db.execute(
        select(DemandeConge)
        .where(DemandeConge.id == demande_id)
        .options(
            selectinload(DemandeConge.demandeur),
            selectinload(DemandeConge.valideur)
        )
    )
    demande = result.scalar_one_or_none()
    
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande de congé non trouvée"
        )
    
    # Vérifier les permissions
    if current_user.role == RoleEnum.EMPLOYE and demande.demandeur_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez voir que vos propres demandes"
        )
    
    return demande

@router.post("/", response_model=DemandeCongeRead)
async def create_demande_conge(
    demande_data: DemandeCongeCreate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Crée une nouvelle demande de congé"""
    demande = DemandeConge(
        **demande_data.dict(),
        demandeur_id=current_user.id
    )
    db.add(demande)
    await db.commit()
    await db.refresh(demande)
    return demande

@router.put("/{demande_id}", response_model=DemandeCongeRead)
async def update_demande_conge(
    demande_id: uuid.UUID,
    demande_data: DemandeCongeUpdate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Met à jour une demande de congé (seulement si en attente et par le demandeur)"""
    result = await db.execute(
        select(DemandeConge).where(DemandeConge.id == demande_id)
    )
    demande = result.scalar_one_or_none()
    
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande de congé non trouvée"
        )
    
    if demande.demandeur_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez modifier que vos propres demandes"
        )
    
    if demande.statut != StatutDemandeEnum.EN_ATTENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les demandes en attente peuvent être modifiées"
        )
    
    update_data = demande_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(demande, field, value)
    
    await db.commit()
    await db.refresh(demande)
    return demande

@router.post("/{demande_id}/valider", response_model=DemandeCongeRead)
async def valider_demande_conge(
    demande_id: uuid.UUID,
    validation_data: DemandeCongeValidation,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_manager())
):
    """Valide ou refuse une demande de congé (Manager/DRH uniquement)"""
    result = await db.execute(
        select(DemandeConge)
        .where(DemandeConge.id == demande_id)
        .options(selectinload(DemandeConge.demandeur))
    )
    demande = result.scalar_one_or_none()
    
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande de congé non trouvée"
        )
    
    if demande.statut != StatutDemandeEnum.EN_ATTENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les demandes en attente peuvent être validées"
        )
    
    # Vérifier que le chef de service peut valider cette demande
    if current_user.role == RoleEnum.CHEF_SERVICE:
        if demande.demandeur.departement_id != current_user.departement_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez valider que les demandes de votre département"
            )
    
    demande.statut = validation_data.statut
    demande.commentaire_validation = validation_data.commentaire_validation
    demande.valideur_id = current_user.id
    demande.date_reponse = datetime.utcnow()
    
    await db.commit()
    await db.refresh(demande)
    return demande

@router.delete("/{demande_id}")
async def cancel_demande_conge(
    demande_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Annule une demande de congé"""
    result = await db.execute(
        select(DemandeConge).where(DemandeConge.id == demande_id)
    )
    demande = result.scalar_one_or_none()
    
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande de congé non trouvée"
        )
    
    if demande.demandeur_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez annuler que vos propres demandes"
        )
    
    if demande.statut == StatutDemandeEnum.REFUSEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une demande refusée ne peut pas être annulée"
        )
    
    demande.statut = StatutDemandeEnum.ANNULEE
    await db.commit()
    return {"message": "Demande annulée avec succès"}

@router.get("/stats/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère les statistiques pour le dashboard selon le rôle"""
    base_query = select(DemandeConge)
    
    # Filtrer selon le rôle
    if current_user.role == RoleEnum.EMPLOYE:
        base_query = base_query.where(DemandeConge.demandeur_id == current_user.id)
    elif current_user.role == RoleEnum.CHEF_SERVICE:
        # Pour chef de service : demandes des employés de son département
        base_query = base_query.where(
            DemandeConge.demandeur_id.in_(
                select(User.id).where(
                    and_(
                        User.departement_id == current_user.departement_id,
                        User.role == RoleEnum.EMPLOYE
                    )
                )
            )
        )
    
    # Statistiques par statut
    stats = {}
    for statut in StatutDemandeEnum:
        result = await db.execute(
            base_query.where(DemandeConge.statut == statut)
        )
        stats[statut.value] = len(result.scalars().all())
    
    return {
        "stats_par_statut": stats,
        "total_demandes": sum(stats.values())
    } 