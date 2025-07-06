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
    DemandeCongeValidation, StatutDemandeEnum, TypeCongeEnum, UserBasicInfo,
    DemandeAnnulation, ActionDynamique, DemandeCongeWithActions
)
from models.user import User, RoleEnum
from models.departement import Departement
from utils.dependencies import get_current_user, require_manager
from utils.date_calculator import calculate_days_details

router = APIRouter(prefix="/demandes-conges", tags=["demandes-conges"])

async def create_user_basic_info_from_db(db: AsyncSession, user_id: uuid.UUID) -> Optional[UserBasicInfo]:
    """Récupère les informations utilisateur de base depuis la DB"""
    result = await db.execute(
        select(User, Departement.nom.label('departement_nom'))
        .outerjoin(Departement, User.departement_id == Departement.id)
        .where(User.id == user_id)
    )
    row = result.first()
    
    if not row:
        return None
    
    user = row[0]
    departement_nom = row[1]
    
    return UserBasicInfo(
        id=user.id,
        nom=user.nom,
        prenom=user.prenom,
        email=user.email,
        role=user.role.value if user.role else None,
        departement=departement_nom
    )

async def enrich_demande_with_user_info(db: AsyncSession, demande: DemandeConge) -> DemandeCongeRead:
    """Enrichit une demande avec les informations utilisateur et valideur"""
    # Récupérer les informations du demandeur
    user_info = await create_user_basic_info_from_db(db, demande.demandeur_id)
    
    # Récupérer les informations du valideur si assigné
    valideur_info = None
    if demande.valideur_id:
        valideur_info = await create_user_basic_info_from_db(db, demande.valideur_id)
    
    demande_dict = {
        'id': demande.id,
        'demandeur_id': demande.demandeur_id,
        'type_conge': demande.type_conge,
        'date_debut': demande.date_debut,
        'date_fin': demande.date_fin,
        'nombre_jours': demande.nombre_jours,
        'working_time': demande.working_time,
        'real_time': demande.real_time,
        'motif': demande.motif,
        'statut': demande.statut,
        'date_demande': demande.date_demande,
        'date_reponse': demande.date_reponse,
        'commentaire_validation': demande.commentaire_validation,
        'valideur_id': demande.valideur_id,
        'created_at': demande.created_at,
        'updated_at': demande.updated_at,
        'user': user_info,
        'valideur': valideur_info
    }
    return DemandeCongeRead(**demande_dict)

@router.get("/", response_model=List[DemandeCongeWithActions])
async def get_demandes_conges(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
    statut: Optional[StatutDemandeEnum] = Query(None),
    type_conge: Optional[TypeCongeEnum] = Query(None),
    limit: int = Query(50, le=100)
):
    """Récupère les demandes de congés selon le rôle de l'utilisateur"""
    query = select(DemandeConge)
    
    # Filtrer selon le rôle
    if current_user.role == RoleEnum.EMPLOYE:
        query = query.where(DemandeConge.demandeur_id == current_user.id)
    elif current_user.role == RoleEnum.CHEF_SERVICE:
        # Le chef de service voit ses demandes + celles de son département
        query = query.where(
            or_(
                DemandeConge.demandeur_id == current_user.id,
                DemandeConge.valideur_id == current_user.id
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
    
    # Enrichir avec les informations utilisateur et les actions
    enriched_demandes = []
    for demande in demandes:
        enriched = await enrich_demande_with_actions(db, demande, current_user)
        enriched_demandes.append(enriched)
    
    return enriched_demandes

@router.get("/mes-demandes", response_model=List[DemandeCongeRead])
async def get_my_demandes(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère les demandes de l'utilisateur connecté"""
    result = await db.execute(
        select(DemandeConge)
        .where(DemandeConge.demandeur_id == current_user.id)
        .order_by(DemandeConge.date_demande.desc())
    )
    demandes = result.scalars().all()
    
    # Enrichir avec les informations utilisateur
    enriched_demandes = []
    for demande in demandes:
        enriched = await enrich_demande_with_user_info(db, demande)
        enriched_demandes.append(enriched)
    
    return enriched_demandes

@router.get("/en-attente", response_model=List[DemandeCongeRead])
async def get_pending_demandes(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_manager())
):
    """Récupère les demandes en attente de validation (Manager/DRH uniquement)"""
    query = select(DemandeConge).where(
        DemandeConge.statut == StatutDemandeEnum.EN_ATTENTE
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
    
    # Enrichir avec les informations utilisateur
    enriched_demandes = []
    for demande in demandes:
        enriched = await enrich_demande_with_user_info(db, demande)
        enriched_demandes.append(enriched)
    
    return enriched_demandes

@router.get("/{demande_id}", response_model=DemandeCongeRead)
async def get_demande_conge(
    demande_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère une demande de congé par son ID"""
    result = await db.execute(
        select(DemandeConge).where(DemandeConge.id == demande_id)
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
    
    return await enrich_demande_with_user_info(db, demande)

@router.post("/", response_model=DemandeCongeRead)
async def create_demande_conge(
    demande_data: DemandeCongeCreate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Crée une nouvelle demande de congé"""
    
    # Calculer automatiquement les jours avec les nouvelles fonctions
    working_days, total_days, formatted_string = calculate_days_details(
        demande_data.date_debut, 
        demande_data.date_fin
    )
    
    # Trouver le valideur approprié selon la hiérarchie
    valideur_id = None
    
    if current_user.role == RoleEnum.CHEF_SERVICE:
        # Si l'utilisateur est chef de service, chercher un DRH pour validation
        drh_result = await db.execute(
            select(User).where(User.role == RoleEnum.DRH).limit(1)
        )
        drh = drh_result.scalar_one_or_none()
        if drh:
            valideur_id = drh.id
            print(f"Chef de service → DRH trouvé: {drh.nom} {drh.prenom} (ID: {drh.id})")
        else:
            print("Aucun DRH trouvé pour valider la demande du chef de service")
            
    elif current_user.role == RoleEnum.EMPLOYE and current_user.departement_id:
        # Pour un employé, chercher le chef de service de son département
        chef_result = await db.execute(
            select(User).where(
                and_(
                    User.departement_id == current_user.departement_id,
                    User.role == RoleEnum.CHEF_SERVICE
                )
            )
        )
        chef_service = chef_result.scalar_one_or_none()
        
        if chef_service:
            valideur_id = chef_service.id
            print(f"Employé → Chef de service trouvé: {chef_service.nom} {chef_service.prenom} (ID: {chef_service.id})")
        else:
            # Pas de chef de service dans le département, chercher un DRH
            drh_result = await db.execute(
                select(User).where(User.role == RoleEnum.DRH).limit(1)
            )
            drh = drh_result.scalar_one_or_none()
            if drh:
                valideur_id = drh.id
                print(f"Pas de chef de service → DRH trouvé: {drh.nom} {drh.prenom} (ID: {drh.id})")
            else:
                print(f"Aucun valideur trouvé (ni chef de service ni DRH)")
    else:
        # Utilisateur sans département ou rôle DRH
        if current_user.role == RoleEnum.DRH:
            print("Utilisateur DRH : pas de valideur automatique assigné")
        else:
            print(f"Utilisateur {current_user.nom} sans département : pas de valideur automatique")
    
    # Créer la demande avec tous les champs calculés
    demande = DemandeConge(
        type_conge=demande_data.type_conge,
        date_debut=demande_data.date_debut,
        date_fin=demande_data.date_fin,
        motif=demande_data.motif,
        nombre_jours=formatted_string,
        working_time=working_days,
        real_time=total_days,
        demandeur_id=current_user.id,
        valideur_id=valideur_id  # Assigner automatiquement le chef de service
    )
    
    db.add(demande)
    await db.commit()
    await db.refresh(demande)
    
    return await enrich_demande_with_user_info(db, demande)

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
    
    # Mettre à jour les champs modifiés
    update_data = demande_data.dict(exclude_unset=True)
    
    # Recalculer les jours si les dates ont changé
    if 'date_debut' in update_data or 'date_fin' in update_data:
        new_date_debut = update_data.get('date_debut', demande.date_debut)
        new_date_fin = update_data.get('date_fin', demande.date_fin)
        
        working_days, total_days, formatted_string = calculate_days_details(
            new_date_debut, 
            new_date_fin
        )
        
        update_data['nombre_jours'] = formatted_string
        update_data['working_time'] = working_days
        update_data['real_time'] = total_days
    
    # Appliquer les modifications
    for field, value in update_data.items():
        setattr(demande, field, value)
    
    demande.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(demande)
    
    return await enrich_demande_with_user_info(db, demande)

@router.post("/{demande_id}/valider", response_model=DemandeCongeRead)
async def valider_demande_conge(
    demande_id: uuid.UUID,
    validation_data: DemandeCongeValidation,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_manager())
):
    """Valide ou refuse une demande de congé (Manager/DRH uniquement)"""
    result = await db.execute(
        select(DemandeConge).where(DemandeConge.id == demande_id)
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
        # Récupérer l'utilisateur demandeur pour vérifier le département
        demandeur_result = await db.execute(
            select(User).where(User.id == demande.demandeur_id)
        )
        demandeur = demandeur_result.scalar_one_or_none()
        
        if not demandeur or demandeur.departement_id != current_user.departement_id:
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
    
    return await enrich_demande_with_user_info(db, demande)

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

async def get_actions_for_demande(demande: DemandeConge, current_user: User) -> list[ActionDynamique]:
    """Calcule les actions disponibles pour une demande selon le rôle et l'état"""
    actions = []
    
    # Employé
    if current_user.role == RoleEnum.EMPLOYE:
        if demande.demandeur_id == current_user.id:  # Ses propres demandes
            if demande.statut == StatutDemandeEnum.EN_ATTENTE:
                actions.extend([
                    ActionDynamique(action="modifier", label="Modifier", icon="edit", color="blue"),
                    ActionDynamique(action="annuler", label="Annuler", icon="trash", color="red")
                ])
            elif demande.statut == StatutDemandeEnum.APPROUVEE:
                actions.append(
                    ActionDynamique(action="demander_annulation", label="Demander annulation", icon="undo", color="orange")
                )
                # Ajouter l'action de téléchargement d'attestation si elle existe
                if demande.attestation_pdf:
                    actions.append(
                        ActionDynamique(action="telecharger_attestation", label="Télécharger attestation", icon="download", color="green")
                    )
    
    # Chef de service
    elif current_user.role == RoleEnum.CHEF_SERVICE:
        if demande.demandeur_id == current_user.id:  # Ses propres demandes
            if demande.statut == StatutDemandeEnum.APPROUVEE:
                actions.append(
                    ActionDynamique(action="demander_annulation", label="Demander annulation", icon="undo", color="orange")
                )
                # Ajouter l'action de téléchargement d'attestation si elle existe
                if demande.attestation_pdf:
                    actions.append(
                        ActionDynamique(action="telecharger_attestation", label="Télécharger attestation", icon="download", color="green")
                    )
        else:  # Demandes de son équipe
            if demande.statut == StatutDemandeEnum.EN_ATTENTE:
                actions.extend([
                    ActionDynamique(action="approuver", label="Approuver", icon="check", color="green"),
                    ActionDynamique(action="refuser", label="Refuser", icon="x", color="red")
                ])
    
    # DRH
    elif current_user.role == RoleEnum.DRH:
        if demande.statut == StatutDemandeEnum.EN_ATTENTE:
            # DRH peut juste voir les demandes en attente, pas les valider directement
            pass
        elif demande.statut == StatutDemandeEnum.APPROUVEE:
            actions.append(
                ActionDynamique(action="generer_attestation", label="Générer attestation", icon="document", color="blue")
            )
        elif demande.statut == StatutDemandeEnum.DEMANDE_ANNULATION:
            actions.extend([
                ActionDynamique(action="approuver_annulation", label="Approuver annulation", icon="check", color="green"),
                ActionDynamique(action="refuser_annulation", label="Refuser annulation", icon="x", color="red")
            ])
    
    # Action de détails disponible pour tous
    actions.append(
        ActionDynamique(action="details", label="Voir détails", icon="eye", color="gray")
    )
    
    return actions

async def enrich_demande_with_actions(db: AsyncSession, demande: DemandeConge, current_user: User) -> DemandeCongeWithActions:
    """Enrichit une demande avec les informations utilisateur et les actions disponibles"""
    # D'abord enrichir avec les informations utilisateur
    enriched_demande = await enrich_demande_with_user_info(db, demande)
    
    # Calculer les actions disponibles
    actions = await get_actions_for_demande(demande, current_user)
    
    # Créer l'objet enrichi avec actions
    demande_with_actions = DemandeCongeWithActions(
        **enriched_demande.dict(),
        actions=actions
    )
    
    return demande_with_actions

@router.post("/{demande_id}/demander-annulation", response_model=DemandeCongeRead)
async def demander_annulation(
    demande_id: uuid.UUID,
    annulation_data: DemandeAnnulation,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Demande l'annulation d'une demande de congé approuvée"""
    result = await db.execute(
        select(DemandeConge).where(DemandeConge.id == demande_id)
    )
    demande = result.scalar_one_or_none()
    
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande de congé non trouvée"
        )
    
    # Vérifier que l'utilisateur peut demander l'annulation
    if current_user.role == RoleEnum.EMPLOYE and demande.demandeur_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez demander l'annulation que de vos propres demandes"
        )
    
    # Vérifier que la demande est approuvée
    if demande.statut != StatutDemandeEnum.APPROUVEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les demandes approuvées peuvent être annulées"
        )
    
    # Marquer la demande comme ayant une demande d'annulation
    demande.statut = StatutDemandeEnum.DEMANDE_ANNULATION
    demande.demande_annulation = True
    demande.motif_annulation = annulation_data.motif_annulation
    demande.date_demande_annulation = datetime.utcnow()
    demande.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(demande)
    
    return await enrich_demande_with_user_info(db, demande)

@router.post("/{demande_id}/traiter-annulation", response_model=DemandeCongeRead)
async def traiter_annulation(
    demande_id: uuid.UUID,
    validation_data: DemandeCongeValidation,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Traite une demande d'annulation (DRH uniquement)"""
    if current_user.role != RoleEnum.DRH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le DRH peut traiter les demandes d'annulation"
        )
    
    result = await db.execute(
        select(DemandeConge).where(DemandeConge.id == demande_id)
    )
    demande = result.scalar_one_or_none()
    
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande de congé non trouvée"
        )
    
    if demande.statut != StatutDemandeEnum.DEMANDE_ANNULATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette demande n'a pas de demande d'annulation en cours"
        )
    
    # Traiter selon la décision du DRH
    if validation_data.statut == StatutDemandeEnum.APPROUVEE:
        # Annulation approuvée → La demande devient annulée
        demande.statut = StatutDemandeEnum.ANNULEE
    else:
        # Annulation refusée → La demande redevient approuvée
        demande.statut = StatutDemandeEnum.APPROUVEE
        demande.demande_annulation = False
    
    demande.commentaire_validation = validation_data.commentaire_validation
    demande.date_reponse = datetime.utcnow()
    demande.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(demande)
    
    return await enrich_demande_with_user_info(db, demande)

@router.get("/{demande_id}/attestation")
async def generer_attestation(
    demande_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Génère une attestation de congé (DRH uniquement)"""
    if current_user.role != RoleEnum.DRH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le DRH peut générer les attestations"
        )
    
    result = await db.execute(
        select(DemandeConge).where(DemandeConge.id == demande_id)
    )
    demande = result.scalar_one_or_none()
    
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande de congé non trouvée"
        )
    
    if demande.statut != StatutDemandeEnum.APPROUVEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les demandes approuvées peuvent générer une attestation"
        )
    
    # Récupérer les informations de l'employé
    enriched_demande = await enrich_demande_with_user_info(db, demande)
    
    # Générer le PDF de l'attestation
    pdf_filename = await generate_attestation_pdf(enriched_demande)
    
    # Mettre à jour la demande avec le nom du fichier PDF
    from datetime import datetime
    demande.attestation_pdf = pdf_filename
    demande.date_generation_attestation = datetime.utcnow()
    await db.commit()
    
    return {
        "message": "Attestation générée avec succès",
        "filename": pdf_filename
    }

async def generate_attestation_pdf(demande: DemandeCongeRead) -> str:
    """Génère une attestation de congé au format PDF"""
    from datetime import datetime
    import os
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
    
    # Créer le nom du fichier PDF
    pdf_filename = f"attestation_conge_{demande.user.nom}_{demande.user.prenom}_{demande.date_debut.strftime('%Y%m%d')}.pdf"
    pdf_path = os.path.join("attestations", pdf_filename)
    
    # Créer le document PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    
    # Obtenir les styles
    styles = getSampleStyleSheet()
    
    # Créer des styles personnalisés
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30*mm,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=5*mm,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=10*mm,
        alignment=TA_JUSTIFY,
        leftIndent=15*mm,
        textColor=colors.black
    )
    
    date_style = ParagraphStyle(
        'CustomDate',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=30*mm,
        alignment=TA_RIGHT,
        textColor=colors.black
    )
    
    signature_style = ParagraphStyle(
        'CustomSignature',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    # Contenu du document
    story = []
    
    # En-tête
    story.append(Paragraph("<b>RÉPUBLIQUE DE CÔTE D'IVOIRE</b>", header_style))
    story.append(Paragraph("Union - Discipline - Travail", header_style))
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("<b>NANGUI ABROGOUA</b>", header_style))
    story.append(Spacer(1, 20*mm))
    
    # Ligne de séparation
    line_table = Table([['_' * 80]], colWidths=[180*mm])
    line_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
    ]))
    story.append(line_table)
    
    # Titre
    story.append(Paragraph("<b><u>ATTESTATION DE CONGÉ</u></b>", title_style))
    
    # Contenu principal  
    story.append(Paragraph(
        f"Nous soussignés organisation Nangui Abrogoua, attestons que Monsieur/Madame "
        f"<b>{demande.user.nom} {demande.user.prenom}</b>, fait partie de notre personnel en qualité de "
        f"<b>{demande.user.role or 'employé'}</b> depuis sa date d'embauche.", 
        content_style
    ))
    
    story.append(Paragraph(
        f"Il bénéficie d'un congé allant du <b>{demande.date_debut.strftime('%d/%m/%Y')}</b> "
        f"au <b>{demande.date_fin.strftime('%d/%m/%Y')}</b> inclus.", 
        content_style
    ))
    
    story.append(Paragraph(
        "En foi de quoi, cette attestation lui est délivrée pour servir et valoir ce que de droit.", 
        content_style
    ))
    
    # Date
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph(f"Fait à Abidjan, le {datetime.now().strftime('%d/%m/%Y')}", date_style))
    
    # Signature
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph("Nom et signature du DRH", signature_style))
    story.append(Spacer(1, 30*mm))
    
    # Ligne de signature
    signature_table = Table([['_' * 30]], colWidths=[80*mm])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
    ]))
    story.append(signature_table)
    
    # Construire le PDF
    doc.build(story)
    
    return pdf_filename


@router.get("/{demande_id}/download-attestation")
async def download_attestation(
    demande_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Télécharge l'attestation PDF d'une demande de congé"""
    import os
    from fastapi.responses import FileResponse
    
    result = await db.execute(
        select(DemandeConge).where(DemandeConge.id == demande_id)
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
            detail="Vous ne pouvez télécharger que vos propres attestations"
        )
    
    # Vérifier qu'une attestation existe
    if not demande.attestation_pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune attestation n'a été générée pour cette demande"
        )
    
    # Vérifier que le fichier existe
    pdf_path = os.path.join("attestations", demande.attestation_pdf)
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Le fichier d'attestation n'a pas été trouvé"
        )
    
    # Retourner le fichier PDF
    return FileResponse(
        path=pdf_path,
        filename=demande.attestation_pdf,
        media_type="application/pdf"
    ) 