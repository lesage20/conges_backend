import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
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
from services.notification_service import NotificationService

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
        # Champs pour les demandes d'annulation
        'demande_annulation': demande.demande_annulation,
        'motif_annulation': demande.motif_annulation,
        'date_demande_annulation': demande.date_demande_annulation,
        # Champs pour l'attestation PDF
        'attestation_pdf': demande.attestation_pdf,
        'attestation_url': demande.attestation_url,
        'date_generation_attestation': demande.date_generation_attestation,
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
        # Chef de service : seulement les demandes de son département (employés)
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

@router.get("/can-create-new")
async def can_create_new_demande(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Vérifie si l'utilisateur peut créer une nouvelle demande de congé"""
    
    # Permettre toujours la création de nouvelles demandes
    # (suppression de la condition qui empêchait la création si une demande était en cours)
    return {
        "can_create": True,
        "reason": None,
        "existing_demande": None
    }

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
    
    # Vérifier les chevauchements avec les demandes existantes
    chevauchement_query = select(DemandeConge).where(
        and_(
            DemandeConge.demandeur_id == current_user.id,
            or_(
                # Cas 1: La nouvelle demande commence pendant une période existante
                and_(
                    DemandeConge.date_debut <= demande_data.date_debut,
                    DemandeConge.date_fin >= demande_data.date_debut
                ),
                # Cas 2: La nouvelle demande se termine pendant une période existante
                and_(
                    DemandeConge.date_debut <= demande_data.date_fin,
                    DemandeConge.date_fin >= demande_data.date_fin
                ),
                # Cas 3: La nouvelle demande englobe une période existante
                and_(
                    DemandeConge.date_debut >= demande_data.date_debut,
                    DemandeConge.date_fin <= demande_data.date_fin
                )
            ),
            # Exclure les demandes refusées et annulées
            DemandeConge.statut.in_([StatutDemandeEnum.EN_ATTENTE, StatutDemandeEnum.APPROUVEE])
        )
    )
    
    result = await db.execute(chevauchement_query)
    demande_chevauchement = result.scalars().first()
    
    if demande_chevauchement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Période de congés en conflit avec une demande existante du {demande_chevauchement.date_debut} au {demande_chevauchement.date_fin}"
        )
    
    # Calculer automatiquement les jours avec les nouvelles fonctions
    working_days, total_days, formatted_string = calculate_days_details(
        demande_data.date_debut, 
        demande_data.date_fin
    )
    
    # Vérifier si l'utilisateur a suffisamment de congés restants
    # (seulement pour les congés payés, pas pour les autres types)
    if demande_data.type_conge == TypeCongeEnum.CONGES_PAYES:
        # Récupérer les demandes de l'utilisateur pour calculer le solde
        demandes_result = await db.execute(
            select(DemandeConge).where(DemandeConge.demandeur_id == current_user.id)
        )
        demandes_existantes = demandes_result.scalars().all()
        
        solde_restant = current_user.calculate_solde_conges_restant(demandes_existantes)
        if working_days > solde_restant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Solde de congés insuffisant. Vous avez {solde_restant} jour(s) restant(s) et vous demandez {working_days} jour(s) ouvrés."
            )
    
    # Trouver le valideur approprié selon la hiérarchie
    valideur_id = None
    statut_initial = StatutDemandeEnum.EN_ATTENTE  # Par défaut
    
    # *** NOUVEAU : Logique spéciale pour le DRH ***
    if current_user.role == RoleEnum.DRH:
        # Les demandes du DRH sont automatiquement approuvées
        statut_initial = StatutDemandeEnum.APPROUVEE
        valideur_id = current_user.id  # Il est son propre valideur
        print(f"DRH {current_user.nom} {current_user.prenom} : demande automatiquement approuvée")
        
    elif current_user.role == RoleEnum.CHEF_SERVICE:
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
        # Pour un employé, vérifier d'abord s'il est dans le département RH
        # Si oui, validation directe par le DRH
        # Sinon, validation par le chef de service puis DRH
        
        # Récupérer le département de l'employé
        dept_result = await db.execute(
            select(Departement).where(Departement.id == current_user.departement_id)
        )
        departement = dept_result.scalar_one_or_none()
        
        # Vérifier si c'est le département RH (par nom)
        if departement and any(keyword in departement.nom.lower() for keyword in 
                              ["ressources humaines", "rh", "drh", "direction des ressources humaines"]):
            # Employé RH : validation directe par le DRH
            drh_result = await db.execute(
                select(User).where(User.role == RoleEnum.DRH).limit(1)
            )
            drh = drh_result.scalar_one_or_none()
            if drh:
                valideur_id = drh.id
                print(f"Employé RH → DRH trouvé: {drh.nom} {drh.prenom} (ID: {drh.id})")
        else:
            # Employé normal : chercher le chef de service de son département
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
        # Utilisateur sans département
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
        valideur_id=valideur_id,
        statut=statut_initial  # EN_ATTENTE ou APPROUVEE selon le cas
    )
    
    # Si c'est automatiquement approuvé (DRH), ajouter la date de réponse
    if statut_initial == StatutDemandeEnum.APPROUVEE:
        demande.date_reponse = datetime.utcnow()
        demande.commentaire_validation = "Approbation automatique (DRH)"
    
    db.add(demande)
    await db.commit()
    await db.refresh(demande)
    
    # Envoyer les notifications pour nouvelle demande (seulement si EN_ATTENTE)
    if statut_initial == StatutDemandeEnum.EN_ATTENTE:
        try:
            notification_service = NotificationService(db)
            await notification_service.notifier_nouvelle_demande(demande)
        except Exception as e:
            # Ne pas faire échouer la création de demande si les notifications échouent
            print(f"Erreur lors de l'envoi des notifications: {e}")
    
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
        
        # Vérifier les chevauchements avec les autres demandes (exclure la demande en cours de modification)
        chevauchement_query = select(DemandeConge).where(
            and_(
                DemandeConge.demandeur_id == current_user.id,
                DemandeConge.id != demande.id,  # Exclure la demande actuelle
                or_(
                    # Cas 1: La demande modifiée commence pendant une période existante
                    and_(
                        DemandeConge.date_debut <= new_date_debut,
                        DemandeConge.date_fin >= new_date_debut
                    ),
                    # Cas 2: La demande modifiée se termine pendant une période existante
                    and_(
                        DemandeConge.date_debut <= new_date_fin,
                        DemandeConge.date_fin >= new_date_fin
                    ),
                    # Cas 3: La demande modifiée englobe une période existante
                    and_(
                        DemandeConge.date_debut >= new_date_debut,
                        DemandeConge.date_fin <= new_date_fin
                    )
                ),
                # Exclure les demandes refusées et annulées
                DemandeConge.statut.in_([StatutDemandeEnum.EN_ATTENTE, StatutDemandeEnum.APPROUVEE])
            )
        )
        
        result = await db.execute(chevauchement_query)
        demande_chevauchement = result.scalars().first()
        
        if demande_chevauchement:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Période de congés en conflit avec une demande existante du {demande_chevauchement.date_debut} au {demande_chevauchement.date_fin}"
            )
        
        working_days, total_days, formatted_string = calculate_days_details(
            new_date_debut, 
            new_date_fin
        )
        
        # Vérifier si l'utilisateur a suffisamment de congés restants pour la modification
        # (seulement pour les congés payés, pas pour les autres types)
        if demande.type_conge == TypeCongeEnum.CONGES_PAYES:
            # Récupérer les demandes de l'utilisateur (excluant la demande en cours de modification)
            demandes_result = await db.execute(
                select(DemandeConge).where(
                    and_(
                        DemandeConge.demandeur_id == current_user.id,
                        DemandeConge.id != demande.id
                    )
                )
            )
            demandes_autres = demandes_result.scalars().all()
            
            # Calculer le solde en excluant la demande actuelle
            solde_avec_demande_actuelle = current_user.calculate_solde_conges_restant(demandes_autres)
            if working_days > solde_avec_demande_actuelle:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Solde de congés insuffisant. Vous avez {solde_avec_demande_actuelle} jour(s) disponible(s) et vous demandez {working_days} jour(s) ouvrés."
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
    
    # Vérifier les permissions de validation
    if current_user.role == RoleEnum.CHEF_SERVICE:
        # Chef de service : seulement les demandes des employés de son département
        demandeur_result = await db.execute(
            select(User).where(User.id == demande.demandeur_id)
        )
        demandeur = demandeur_result.scalar_one_or_none()
        
        if not demandeur or demandeur.departement_id != current_user.departement_id or demandeur.role != RoleEnum.EMPLOYE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez valider que les demandes des employés de votre département"
            )
    
    elif current_user.role == RoleEnum.DRH:
        # DRH peut valider :
        # 1. Demandes des chefs de service
        # 2. Demandes des employés RH
        # 3. Demandes des employés de son département (si il en a un)
        demandeur_result = await db.execute(
            select(User).where(User.id == demande.demandeur_id)
        )
        demandeur = demandeur_result.scalar_one_or_none()
        
        if not demandeur:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demandeur non trouvé"
            )
        
        can_validate = False
        
        # 1. Peut valider les demandes des chefs de service
        if demandeur.role == RoleEnum.CHEF_SERVICE:
            can_validate = True
        
        # 2. Peut valider les demandes des employés RH (département contenant "RH", "ressources humaines", etc.)
        elif demandeur.role == RoleEnum.EMPLOYE and demandeur.departement_id:
            # Récupérer le département du demandeur
            dept_result = await db.execute(
                select(Departement).where(Departement.id == demandeur.departement_id)
            )
            dept_demandeur = dept_result.scalar_one_or_none()
            
            if dept_demandeur and any(keyword in dept_demandeur.nom.lower() for keyword in 
                                    ["ressources humaines", "rh", "drh", "direction des ressources humaines"]):
                can_validate = True
        
        # 3. Peut valider les demandes des employés de son département (si le DRH a un département)
        if not can_validate and current_user.departement_id and demandeur.departement_id == current_user.departement_id and demandeur.role == RoleEnum.EMPLOYE:
            can_validate = True
        
        if not can_validate:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez valider cette demande selon votre périmètre de responsabilité"
            )
    
    demande.statut = validation_data.statut
    demande.commentaire_validation = validation_data.commentaire_validation
    demande.valideur_id = current_user.id
    demande.date_reponse = datetime.utcnow()
    
    await db.commit()
    await db.refresh(demande)
    
    # Envoyer les notifications de validation
    try:
        notification_service = NotificationService(db)
        approuvee = validation_data.statut == StatutDemandeEnum.APPROUVEE
        await notification_service.notifier_validation_demande(
            demande, 
            approuvee, 
            validation_data.commentaire_validation
        )
    except Exception as e:
        # Ne pas faire échouer la validation si les notifications échouent
        print(f"Erreur lors de l'envoi des notifications: {e}")
    
    return await enrich_demande_with_user_info(db, demande)

@router.delete("/{demande_id}")
async def delete_demande_conge(
    demande_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Supprime définitivement une demande de congé"""
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
            detail="Vous ne pouvez supprimer que vos propres demandes"
        )
    elif current_user.role == RoleEnum.CHEF_SERVICE:
        # Chef de service peut supprimer les demandes de son équipe
        if demande.demandeur_id != current_user.id:
            # Vérifier si le demandeur est dans son département
            demandeur_result = await db.execute(
                select(User).where(User.id == demande.demandeur_id)
            )
            demandeur = demandeur_result.scalar_one_or_none()
            if not demandeur or demandeur.departement_id != current_user.departement_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Vous ne pouvez supprimer que les demandes de votre équipe"
                )
    # DRH peut supprimer toutes les demandes (pas de vérification supplémentaire)
    
    # Vérifier que seules les demandes en attente ou refusées peuvent être supprimées
    if demande.statut not in [StatutDemandeEnum.EN_ATTENTE, StatutDemandeEnum.REFUSEE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les demandes en attente ou refusées peuvent être supprimées définitivement"
        )
    
    # Suppression définitive de la base de données
    await db.delete(demande)
    await db.commit()
    return {"message": "Demande supprimée définitivement avec succès"}


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
        # Chef de service : demandes des employés de son département
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
    # DRH : garder toutes les demandes pour les stats globales
    
    # Statistiques par statut
    stats = {}
    for statut in StatutDemandeEnum:
        result = await db.execute(
            base_query.where(DemandeConge.statut == statut)
        )
        stats[statut.value] = len(result.scalars().all())
    
    # KPI spécifiques aux employés
    if current_user.role == RoleEnum.EMPLOYE:
        # Récupérer toutes les demandes de l'utilisateur pour calculer le solde restant
        demandes_user_result = await db.execute(
            select(DemandeConge).where(DemandeConge.demandeur_id == current_user.id)
        )
        demandes_user = demandes_user_result.scalars().all()
        
        # Calculer le solde restant avec la méthode officielle
        solde_restant = current_user.calculate_solde_conges_restant(demandes_user)
        
        # Calculer les statistiques pour l'année en cours
        annee_courante = date.today().year
        debut_annee = date(annee_courante, 1, 1)
        fin_annee = date(annee_courante, 12, 31)
        
        # Jours déjà pris (demandes approuvées cette année)
        demandes_approuvees_annee = [d for d in demandes_user 
                                   if d.statut == StatutDemandeEnum.APPROUVEE 
                                   and d.date_debut >= debut_annee 
                                   and d.date_debut <= fin_annee]
        jours_pris = sum(demande.working_time or 0 for demande in demandes_approuvees_annee)
        
        # Jours en attente (demandes en attente cette année)
        demandes_attente_annee = [d for d in demandes_user 
                                if d.statut == StatutDemandeEnum.EN_ATTENTE 
                                and d.date_debut >= debut_annee 
                                and d.date_debut <= fin_annee]
        jours_attente = sum(demande.working_time or 0 for demande in demandes_attente_annee)
        
        # Jours restants (en utilisant le solde restant global, pas seulement pour l'année)
        jours_restants = solde_restant
        
        # Vérifier si l'employé a un congé en cours
        aujourd_hui = date.today()
        conge_actuel = None
        for demande in demandes_user:
            if (demande.statut == StatutDemandeEnum.APPROUVEE and 
                demande.date_debut <= aujourd_hui and 
                demande.date_fin >= aujourd_hui):
                conge_actuel = demande
                break
        
        # Activité récente (toutes les demandes de l'employé)
        # Utiliser les demandes déjà récupérées et les trier
        demandes_triees = sorted(demandes_user, key=lambda d: d.created_at, reverse=True)[:5]
        
        activite_list = []
        for demande in demandes_triees:
            activite_list.append({
                "id": str(demande.id),
                "message": f"Demande de congé {demande.statut.value}",
                "type": demande.statut.value,
                "date_debut": demande.date_debut.strftime('%d/%m/%Y'),
                "date_fin": demande.date_fin.strftime('%d/%m/%Y'),
                "working_time": demande.working_time,
                "motif": demande.motif,
                "time": demande.created_at.strftime('%d/%m/%Y')
            })
        
        kpi_data = {
            "demandes_approuvees": stats.get("approuvee", 0),
            "demandes_refusees": stats.get("refusee", 0),
            "demandes_en_attente": stats.get("en_attente", 0),
            "jours_restants": jours_restants,
            "solde_total": current_user.solde_conges,
            "solde_conges_restant": solde_restant,
            "jours_pris": jours_pris,
            "jours_en_attente": jours_attente,
            "annee": annee_courante,
            "activite_recente": activite_list
        }
        
        # Ajouter les infos du congé en cours s'il y en a un
        if conge_actuel:
            jours_restants_conge = (conge_actuel.date_fin - aujourd_hui).days + 1
            kpi_data["conge_en_cours"] = {
                "date_debut": conge_actuel.date_debut.strftime('%d/%m/%Y'),
                "date_fin": conge_actuel.date_fin.strftime('%d/%m/%Y'),
                "jours_restants": max(0, jours_restants_conge),
                "motif": conge_actuel.motif
            }
        
        return {
            "stats_par_statut": stats,
            "total_demandes": sum(stats.values()),
            "kpi_employe": kpi_data
        }
    
    # KPI spécifiques aux chefs de service
    elif current_user.role == RoleEnum.CHEF_SERVICE:
        annee_courante = date.today().year
        debut_annee = date(annee_courante, 1, 1)
        fin_annee = date(annee_courante, 12, 31)
        aujourd_hui = date.today()
        
        # Récupérer tous les employés du département
        employes_departement = await db.execute(
            select(User).where(
                and_(
                    User.departement_id == current_user.departement_id,
                    User.role == RoleEnum.EMPLOYE
                )
            )
        )
        employes = employes_departement.scalars().all()
        
        # Calculer les stats de l'équipe correctement
        stats_equipe = {
            "approuvee": 0,
            "refusee": 0,
            "en_attente": 0,
            "demande_annulation": 0,
            "annulee": 0
        }
        
        # Compter toutes les demandes de l'équipe
        for statut in StatutDemandeEnum:
            result = await db.execute(
                select(DemandeConge).where(
                    and_(
                        DemandeConge.demandeur_id.in_([emp.id for emp in employes]),
                        DemandeConge.statut == statut
                    )
                )
            )
            stats_equipe[statut.value] = len(result.scalars().all())
        
        # Employés actuellement en congé
        conges_en_cours = await db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.demandeur_id.in_([emp.id for emp in employes]),
                    DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                    DemandeConge.date_debut <= aujourd_hui,
                    DemandeConge.date_fin >= aujourd_hui
                )
            )
        )
        conges_actuels = conges_en_cours.scalars().all()
        
        # Informations sur les employés en congé
        employes_en_conge = []
        for conge in conges_actuels:
            employe = next((emp for emp in employes if emp.id == conge.demandeur_id), None)
            if employe:
                jours_restants = (conge.date_fin - aujourd_hui).days + 1
                employes_en_conge.append({
                    "nom": f"{employe.prenom} {employe.nom}",
                    "date_debut": conge.date_debut.strftime('%d/%m/%Y'),
                    "date_fin": conge.date_fin.strftime('%d/%m/%Y'),
                    "jours_restants": max(0, jours_restants),
                    "motif": conge.motif,
                    "working_time": conge.working_time
                })
        
        # Prochain retour de congé
        prochain_retour = None
        if employes_en_conge:
            prochain_retour = min(employes_en_conge, key=lambda x: x["jours_restants"])
        
        # Prochains départs en congé (5 plus anciens pas encore partis)
        prochains_departs = await db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.demandeur_id.in_([emp.id for emp in employes]),
                    DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                    DemandeConge.date_debut > aujourd_hui
                )
            ).order_by(DemandeConge.date_debut.asc()).limit(5)
        )
        
        prochains_departs_list = []
        for conge in prochains_departs.scalars().all():
            employe = next((emp for emp in employes if emp.id == conge.demandeur_id), None)
            if employe:
                jours_avant_depart = (conge.date_debut - aujourd_hui).days
                prochains_departs_list.append({
                    "nom": f"{employe.prenom} {employe.nom}",
                    "date_debut": conge.date_debut.strftime('%d/%m/%Y'),
                    "date_fin": conge.date_fin.strftime('%d/%m/%Y'),
                    "jours_avant_depart": jours_avant_depart,
                    "motif": conge.motif,
                    "working_time": conge.working_time
                })
        
        # Ses propres infos de congés (comme employé)
        mes_demandes_approuvees = await db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.demandeur_id == current_user.id,
                    DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                    DemandeConge.date_debut >= debut_annee,
                    DemandeConge.date_debut <= fin_annee
                )
            )
        )
        mes_jours_pris = sum(demande.working_time or 0 for demande in mes_demandes_approuvees.scalars().all())
        
        mes_demandes_attente = await db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.demandeur_id == current_user.id,
                    DemandeConge.statut == StatutDemandeEnum.EN_ATTENTE,
                    DemandeConge.date_debut >= debut_annee,
                    DemandeConge.date_debut <= fin_annee
                )
            )
        )
        mes_jours_attente = sum(demande.working_time or 0 for demande in mes_demandes_attente.scalars().all())
        
        mes_jours_restants = max(0, current_user.solde_conges - mes_jours_pris - mes_jours_attente)
        
        # Vérifier si le chef a un congé en cours
        mon_conge_en_cours = await db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.demandeur_id == current_user.id,
                    DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                    DemandeConge.date_debut <= aujourd_hui,
                    DemandeConge.date_fin >= aujourd_hui
                )
            )
        )
        mon_conge_actuel = mon_conge_en_cours.scalar_one_or_none()
        
        # Activité récente de l'équipe
        activite_equipe = await db.execute(
            select(DemandeConge).where(
                DemandeConge.demandeur_id.in_([emp.id for emp in employes])
            ).order_by(DemandeConge.created_at.desc()).limit(8)
        )
        
        activite_list = []
        for demande in activite_equipe.scalars().all():
            # Récupérer le nom de l'employé
            employe = next((emp for emp in employes if emp.id == demande.demandeur_id), None)
            nom_employe = f"{employe.prenom} {employe.nom}" if employe else "Employé"
            
            # Définir le message selon le statut
            if demande.statut == StatutDemandeEnum.APPROUVEE:
                message = f"{nom_employe} - Congé approuvé"
            elif demande.statut == StatutDemandeEnum.REFUSEE:
                message = f"{nom_employe} - Congé refusé"
            elif demande.statut == StatutDemandeEnum.EN_ATTENTE:
                message = f"{nom_employe} - Demande en attente"
            elif demande.statut == StatutDemandeEnum.DEMANDE_ANNULATION:
                message = f"{nom_employe} - Demande d'annulation"
            else:
                message = f"{nom_employe} - Demande {demande.statut.value}"
            
            activite_list.append({
                "id": str(demande.id),
                "message": message,
                "type": demande.statut.value,
                "date_debut": demande.date_debut.strftime('%d/%m/%Y'),
                "date_fin": demande.date_fin.strftime('%d/%m/%Y'),
                "working_time": demande.working_time,
                "motif": demande.motif,
                "time": demande.created_at.strftime('%d/%m/%Y à %H:%M'),
                "employe": nom_employe
            })
        
        kpi_data = {
            # Stats de l'équipe
            "equipe": {
                "demandes_approuvees": stats_equipe.get("approuvee", 0),
                "demandes_refusees": stats_equipe.get("refusee", 0),
                "demandes_en_attente": stats_equipe.get("en_attente", 0),
                "demandes_annulation": stats_equipe.get("demande_annulation", 0),
                "total_demandes": sum(stats_equipe.values()),
                "activite_recente": activite_list,
                "employes_en_conge": employes_en_conge,
                "prochain_retour": prochain_retour,
                "prochains_departs": prochains_departs_list,
                "nombre_employes": len(employes),
                "employes_presents": len(employes) - len(employes_en_conge)
            },
            # Ses propres congés
            "mes_conges": {
                "jours_restants": mes_jours_restants,
                "solde_total": current_user.solde_conges,
                "jours_pris": mes_jours_pris,
                "jours_en_attente": mes_jours_attente,
                "annee": annee_courante
            }
        }
        
        # Ajouter ses infos de congé en cours s'il y en a un
        if mon_conge_actuel:
            jours_restants_conge = (mon_conge_actuel.date_fin - aujourd_hui).days + 1
            kpi_data["mes_conges"]["conge_en_cours"] = {
                "date_debut": mon_conge_actuel.date_debut.strftime('%d/%m/%Y'),
                "date_fin": mon_conge_actuel.date_fin.strftime('%d/%m/%Y'),
                "jours_restants": max(0, jours_restants_conge),
                "motif": mon_conge_actuel.motif
            }
        
        return {
            "stats_par_statut": stats_equipe,
            "total_demandes": sum(stats_equipe.values()),
            "kpi_chef_service": kpi_data
        }
    
    # KPI spécifiques aux DRH
    elif current_user.role == RoleEnum.DRH:
        annee_courante = date.today().year
        debut_annee = date(annee_courante, 1, 1)
        fin_annee = date(annee_courante, 12, 31)
        aujourd_hui = date.today()
        
        # Récupérer tous les départements
        departements_result = await db.execute(select(Departement))
        departements = departements_result.scalars().all()
        
        # Statistiques par département
        stats_departements = []
        for dept in departements:
            # Récupérer les employés du département
            employes_dept = await db.execute(
                select(User).where(
                    and_(
                        User.departement_id == dept.id,
                        User.role.in_([RoleEnum.EMPLOYE, RoleEnum.CHEF_SERVICE])
                    )
                )
            )
            employes_list = employes_dept.scalars().all()
            
            # Statistiques des demandes du département
            stats_dept = {
                "approuvee": 0,
                "refusee": 0,
                "en_attente": 0,
                "demande_annulation": 0,
                "annulee": 0
            }
            
            if employes_list:
                for statut in StatutDemandeEnum:
                    result = await db.execute(
                        select(DemandeConge).where(
                            and_(
                                DemandeConge.demandeur_id.in_([emp.id for emp in employes_list]),
                                DemandeConge.statut == statut
                            )
                        )
                    )
                    stats_dept[statut.value] = len(result.scalars().all())
            
            # Employés actuellement en congé
            conges_en_cours = await db.execute(
                select(DemandeConge).where(
                    and_(
                        DemandeConge.demandeur_id.in_([emp.id for emp in employes_list]),
                        DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                        DemandeConge.date_debut <= aujourd_hui,
                        DemandeConge.date_fin >= aujourd_hui
                    )
                )
            )
            employes_en_conge = len(conges_en_cours.scalars().all())
            
            stats_departements.append({
                "id": str(dept.id),
                "nom": dept.nom,
                "nombre_employes": len(employes_list),
                "employes_presents": len(employes_list) - employes_en_conge,
                "employes_en_conge": employes_en_conge,
                "demandes_approuvees": stats_dept.get("approuvee", 0),
                "demandes_refusees": stats_dept.get("refusee", 0),
                "demandes_en_attente": stats_dept.get("en_attente", 0),
                "demandes_annulation": stats_dept.get("demande_annulation", 0),
                "total_demandes": sum(stats_dept.values()),
                "solde_total": sum(emp.solde_conges or 0 for emp in employes_list),
                "taux_presence": round((len(employes_list) - employes_en_conge) / len(employes_list) * 100, 1) if employes_list else 0
            })
        
        # Calculer les stats globales
        stats_globales = {
            "approuvee": sum(dept["demandes_approuvees"] for dept in stats_departements),
            "refusee": sum(dept["demandes_refusees"] for dept in stats_departements),
            "en_attente": sum(dept["demandes_en_attente"] for dept in stats_departements),
            "demande_annulation": sum(dept["demandes_annulation"] for dept in stats_departements),
        }
        
        # Calculer les KPI globaux de l'organisation
        total_employes = sum(dept["nombre_employes"] for dept in stats_departements)
        total_absents = sum(dept["employes_en_conge"] for dept in stats_departements)
        total_presents = total_employes - total_absents
        
        # Calculer les futurs absents du mois courant
        debut_mois = aujourd_hui.replace(day=1)
        fin_mois = debut_mois.replace(month=debut_mois.month + 1) if debut_mois.month < 12 else debut_mois.replace(year=debut_mois.year + 1, month=1)
        fin_mois = fin_mois.replace(day=1) - timedelta(days=1)
        
        # Récupérer tous les employés
        tous_employes = []
        for dept in departements:
            employes_dept = await db.execute(
                select(User).where(
                    and_(
                        User.departement_id == dept.id,
                        User.role.in_([RoleEnum.EMPLOYE, RoleEnum.CHEF_SERVICE])
                    )
                )
            )
            tous_employes.extend(employes_dept.scalars().all())
        
        # Congés approuvés qui touchent le mois courant
        conges_mois_courant = await db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.demandeur_id.in_([emp.id for emp in tous_employes]),
                    DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                    or_(
                        # Congés qui commencent dans le mois
                        and_(
                            DemandeConge.date_debut >= debut_mois,
                            DemandeConge.date_debut <= fin_mois
                        ),
                        # Congés qui se terminent dans le mois
                        and_(
                            DemandeConge.date_fin >= debut_mois,
                            DemandeConge.date_fin <= fin_mois
                        ),
                        # Congés qui englobent le mois
                        and_(
                            DemandeConge.date_debut <= debut_mois,
                            DemandeConge.date_fin >= fin_mois
                        )
                    )
                )
            )
        )
        
        # Compter les employés uniques qui seront absents ce mois
        employes_absents_mois = set()
        for conge in conges_mois_courant.scalars().all():
            employes_absents_mois.add(conge.demandeur_id)
        
        total_absents_mois_courant = len(employes_absents_mois)
        
        # Ses propres infos de congés (comme employé)
        mes_demandes_approuvees = await db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.demandeur_id == current_user.id,
                    DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                    DemandeConge.date_debut >= debut_annee,
                    DemandeConge.date_debut <= fin_annee
                )
            )
        )
        mes_jours_pris = sum(demande.working_time or 0 for demande in mes_demandes_approuvees.scalars().all())
        
        mes_demandes_attente = await db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.demandeur_id == current_user.id,
                    DemandeConge.statut == StatutDemandeEnum.EN_ATTENTE,
                    DemandeConge.date_debut >= debut_annee,
                    DemandeConge.date_debut <= fin_annee
                )
            )
        )
        mes_jours_attente = sum(demande.working_time or 0 for demande in mes_demandes_attente.scalars().all())
        
        mes_jours_restants = max(0, current_user.solde_conges - mes_jours_pris - mes_jours_attente)
        
        # Vérifier si le DRH a un congé en cours
        mon_conge_en_cours = await db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.demandeur_id == current_user.id,
                    DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                    DemandeConge.date_debut <= aujourd_hui,
                    DemandeConge.date_fin >= aujourd_hui
                )
            )
        )
        mon_conge_actuel = mon_conge_en_cours.scalar_one_or_none()
        
        # Activité récente de toute l'organisation
        activite_generale = await db.execute(
            select(DemandeConge)
            .join(User, DemandeConge.demandeur_id == User.id)
            .where(User.role.in_([RoleEnum.EMPLOYE, RoleEnum.CHEF_SERVICE]))
            .order_by(DemandeConge.created_at.desc())
            .limit(5)
        )
        
        activite_list = []
        for demande in activite_generale.scalars().all():
            # Récupérer l'utilisateur
            result_user = await db.execute(
                select(User).where(User.id == demande.demandeur_id)
            )
            employe = result_user.scalar_one_or_none()
            if employe:
                nom_employe = f"{employe.prenom} {employe.nom}"
                nom_dept = employe.departement.nom if employe.departement else "Département non défini"
                
                # Définir le message selon le statut
                if demande.statut == StatutDemandeEnum.APPROUVEE:
                    message = f"{nom_employe} ({nom_dept}) - Congé approuvé"
                elif demande.statut == StatutDemandeEnum.REFUSEE:
                    message = f"{nom_employe} ({nom_dept}) - Congé refusé"
                elif demande.statut == StatutDemandeEnum.EN_ATTENTE:
                    message = f"{nom_employe} ({nom_dept}) - Demande en attente"
                elif demande.statut == StatutDemandeEnum.DEMANDE_ANNULATION:
                    message = f"{nom_employe} ({nom_dept}) - Demande d'annulation"
                else:
                    message = f"{nom_employe} ({nom_dept}) - Demande {demande.statut.value}"
                
                activite_list.append({
                    "id": str(demande.id),
                    "message": message,
                    "type": demande.statut.value,
                    "date_debut": demande.date_debut.strftime('%d/%m/%Y'),
                    "date_fin": demande.date_fin.strftime('%d/%m/%Y'),
                    "working_time": demande.working_time,
                    "motif": demande.motif,
                    "time": demande.created_at.strftime('%d/%m/%Y à %H:%M'),
                    "employe": nom_employe,
                    "departement": nom_dept
                })
        
        kpi_data = {
            # Vue d'ensemble par département
            "departements": stats_departements,
            # Stats globales
            "stats_globales": stats_globales,
            # KPI globaux de l'organisation
            "kpi_globaux": {
                "total_employes": total_employes,
                "total_absents": total_absents,
                "total_presents": total_presents,
                "total_absents_mois_courant": total_absents_mois_courant,
                "pourcentage_presence": round((total_presents / total_employes * 100), 1) if total_employes > 0 else 0,
                "pourcentage_absence": round((total_absents / total_employes * 100), 1) if total_employes > 0 else 0,
                "pourcentage_absents_mois": round((total_absents_mois_courant / total_employes * 100), 1) if total_employes > 0 else 0,
                "mois_courant": aujourd_hui.strftime("%B %Y")
            },
            # Activité récente
            "activite_recente": activite_list,
            # Mes propres congés
            "mes_conges": {
                "jours_restants": mes_jours_restants,
                "solde_total": current_user.solde_conges,
                "jours_pris": mes_jours_pris,
                "jours_en_attente": mes_jours_attente,
                "annee": annee_courante
            },
            # Totaux organisation (anciens - pour compatibilité)
            "totaux": {
                "nombre_employes": total_employes,
                "employes_presents": total_presents,
                "employes_en_conge": total_absents,
                "solde_total_organisation": sum(dept["solde_total"] for dept in stats_departements)
            }
        }
        
        # Ajouter ses infos de congé en cours s'il y en a un
        if mon_conge_actuel:
            jours_restants_conge = (mon_conge_actuel.date_fin - aujourd_hui).days + 1
            kpi_data["mes_conges"]["conge_en_cours"] = {
                "date_debut": mon_conge_actuel.date_debut.strftime('%d/%m/%Y'),
                "date_fin": mon_conge_actuel.date_fin.strftime('%d/%m/%Y'),
                "jours_restants": max(0, jours_restants_conge),
                "motif": mon_conge_actuel.motif
            }
        
        return {
            "stats_par_statut": stats_globales,
            "total_demandes": sum(stats_globales.values()),
            "kpi_drh": kpi_data
        }
    
    return {
        "stats_par_statut": stats,
        "total_demandes": sum(stats.values())
    }

async def get_actions_for_demande(demande: DemandeConge, current_user: User) -> list[ActionDynamique]:
    """Détermine les actions disponibles pour une demande selon le rôle de l'utilisateur"""
    actions = []
    
    # Employé
    if current_user.role == RoleEnum.EMPLOYE:
        # Seulement pour ses propres demandes
        if demande.demandeur_id != current_user.id:
            return actions
        
        if demande.statut == StatutDemandeEnum.EN_ATTENTE:
            actions.extend([
                ActionDynamique(action="modifier", label="Modifier", icon="edit", color="blue"),
                ActionDynamique(action="annuler", label="Supprimer", icon="trash", color="red")
            ])
        elif demande.statut == StatutDemandeEnum.APPROUVEE:
            actions.append(
                ActionDynamique(action="demander_annulation", label="Demander annulation", icon="undo", color="orange")
            )
            # Ajouter l'action de téléchargement d'attestation si elle existe
            if demande.attestation_url:
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
                if demande.attestation_url:
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
        if demande.demandeur_id == current_user.id:  # Ses propres demandes (auto-approuvées)
            if demande.statut == StatutDemandeEnum.APPROUVEE:
                actions.append(
                    ActionDynamique(action="generer_attestation", label="Générer attestation", icon="document", color="blue")
                )
        else:  # Demandes des autres
            if demande.statut == StatutDemandeEnum.EN_ATTENTE:
                # Le DRH peut valider les demandes des chefs de service et des employés RH
                # Plus celles de son équipe si il a un département assigné
                can_validate = False
                
                # Récupérer le demandeur pour vérifier son rôle et département
                # Note: On devrait passer ces infos en paramètre pour éviter les requêtes DB ici
                # Mais pour simplifier, on assume que le DRH peut valider selon sa logique métier
                # Cette logique sera vérifiée dans l'endpoint de validation
                can_validate = True  # Le DRH peut potentiellement valider toutes les demandes en attente
                
                if can_validate:
                    actions.extend([
                        ActionDynamique(action="approuver", label="Approuver", icon="check", color="green"),
                        ActionDynamique(action="refuser", label="Refuser", icon="x", color="red")
                    ])
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
    request: Request,
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
    
    # Construire l'URL complète de l'attestation
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    attestation_url = f"{base_url}/attestations/{pdf_filename}"
    
    # Mettre à jour la demande avec le nom du fichier PDF et l'URL
    demande.attestation_pdf = pdf_filename
    demande.attestation_url = attestation_url
    demande.date_generation_attestation = datetime.utcnow()
    await db.commit()
    
    return {
        "message": "Attestation générée avec succès",
        "filename": pdf_filename,
        "url": attestation_url
    }

async def generate_attestation_pdf(demande: DemandeCongeRead) -> str:
    """Génère une attestation de congé au format PDF"""
    import os
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    
    # Créer le nom du fichier PDF (sans caractères spéciaux)
    nom_clean = ''.join(c for c in demande.user.nom if c.isalnum())
    prenom_clean = ''.join(c for c in demande.user.prenom if c.isalnum())
    pdf_filename = f"attestation_{nom_clean}_{prenom_clean}_{demande.date_debut.strftime('%Y%m%d')}.pdf"
    pdf_path = os.path.join("attestations", pdf_filename)
    
    try:
        # Créer le canvas
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        
        # Variables pour simplifier
        left_margin = 50
        y_pos = height - 100
        
        # En-tête centré
        c.setFont("Helvetica-Bold", 14)
        title1 = "RÉPUBLIQUE DE CÔTE D'IVOIRE"
        text_width = c.stringWidth(title1, "Helvetica-Bold", 14)
        c.drawString((width - text_width) / 2, y_pos, title1)
        y_pos -= 20
        
        c.setFont("Helvetica", 12)
        title2 = "Union - Discipline - Travail"
        text_width = c.stringWidth(title2, "Helvetica", 12)
        c.drawString((width - text_width) / 2, y_pos, title2)
        y_pos -= 40
        
        c.setFont("Helvetica-Bold", 12)
        title3 = "ENTREPRISE"
        text_width = c.stringWidth(title3, "Helvetica-Bold", 12)
        c.drawString((width - text_width) / 2, y_pos, title3)
        y_pos -= 40
        
        # Ligne de séparation
        c.line(left_margin, y_pos, width - left_margin, y_pos)
        y_pos -= 40
        
        # Titre principal
        c.setFont("Helvetica-Bold", 16)
        main_title = "ATTESTATION DE CONGÉ"
        text_width = c.stringWidth(main_title, "Helvetica-Bold", 16)
        c.drawString((width - text_width) / 2, y_pos, main_title)
        y_pos -= 60
        
        # Contenu
        c.setFont("Helvetica", 12)
        
        # Données
        nom_complet = f"{demande.user.nom} {demande.user.prenom}"
        role_text = demande.user.role or "employe"
        date_debut = demande.date_debut.strftime('%d/%m/%Y')
        date_fin = demande.date_fin.strftime('%d/%m/%Y')
        date_today = datetime.now().strftime('%d/%m/%Y')
        
        # Paragraphe 1
        text1 = "Nous soussignés entreprise, attestons que"
        c.drawString(left_margin, y_pos, text1)
        y_pos -= 15
        
        text2 = f"Monsieur/Madame {nom_complet}, fait partie de notre personnel"
        c.drawString(left_margin, y_pos, text2)
        y_pos -= 15
        
        text3 = f"en qualité de {role_text} depuis sa date d'embauche."
        c.drawString(left_margin, y_pos, text3)
        y_pos -= 30
        
        # Paragraphe 2
        text4 = f"Il bénéficie d'un congé allant du {date_debut} au {date_fin} inclus."
        c.drawString(left_margin, y_pos, text4)
        y_pos -= 30
        
        # Paragraphe 3
        text5 = "En foi de quoi, cette attestation lui est délivrée pour servir"
        c.drawString(left_margin, y_pos, text5)
        y_pos -= 15
        
        text6 = "et valoir ce que de droit."
        c.drawString(left_margin, y_pos, text6)
        y_pos -= 60
        
        # Date (alignée à droite)
        date_text = f"Fait à Abidjan, le {date_today}"
        text_width = c.stringWidth(date_text, "Helvetica", 12)
        c.drawString(width - left_margin - text_width, y_pos, date_text)
        y_pos -= 80
        
        # Signature centrée
        signature_text = "Nom et signature du DRH"
        text_width = c.stringWidth(signature_text, "Helvetica", 12)
        c.drawString((width - text_width) / 2, y_pos, signature_text)
        y_pos -= 30
        
        # Ligne de signature
        line_length = 150
        start_x = (width - line_length) / 2
        end_x = start_x + line_length
        c.line(start_x, y_pos, end_x, y_pos)
        
        # Sauvegarder
        c.save()
        
        print(f"PDF généré avec succès: {pdf_path}")
        return pdf_filename
        
    except Exception as e:
        print(f"Erreur lors de la génération du PDF: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération du PDF: {str(e)}"
        )

@router.get("/calendrier/{year}/{month}")
async def get_calendrier_conges(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère les congés approuvés pour un mois donné pour l'affichage du calendrier"""
    from datetime import date
    
    # Créer les dates de début et fin du mois
    debut_mois = date(year, month, 1)
    if month == 12:
        fin_mois = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        fin_mois = date(year, month + 1, 1) - timedelta(days=1)
    
    # Déterminer quels congés voir selon le rôle
    if current_user.role == RoleEnum.EMPLOYE:
        # Employé : seulement ses propres congés
        query = select(DemandeConge).where(
            and_(
                DemandeConge.demandeur_id == current_user.id,
                DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                or_(
                    # Congés qui commencent dans le mois
                    and_(
                        DemandeConge.date_debut >= debut_mois,
                        DemandeConge.date_debut <= fin_mois
                    ),
                    # Congés qui se terminent dans le mois
                    and_(
                        DemandeConge.date_fin >= debut_mois,
                        DemandeConge.date_fin <= fin_mois
                    ),
                    # Congés qui englobent le mois
                    and_(
                        DemandeConge.date_debut <= debut_mois,
                        DemandeConge.date_fin >= fin_mois
                    )
                )
            )
        )
    
    elif current_user.role == RoleEnum.CHEF_SERVICE :
        # Chef de service : congés de son département
        query = select(DemandeConge).where(
            and_(
                DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                DemandeConge.valideur_id == current_user.id,
                or_(
                    and_(
                        DemandeConge.date_debut >= debut_mois,
                        DemandeConge.date_debut <= fin_mois
                    ),
                    and_(
                        DemandeConge.date_fin >= debut_mois,
                        DemandeConge.date_fin <= fin_mois
                    ),
                    and_(
                        DemandeConge.date_debut <= debut_mois,
                        DemandeConge.date_fin >= fin_mois
                    )
                )
            )
        )
    
    else:  # DRH
        # DRH : tous les congés de l'organisation
        query = select(DemandeConge).where(
            and_(
                DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                or_(
                    and_(
                        DemandeConge.date_debut >= debut_mois,
                        DemandeConge.date_debut <= fin_mois
                    ),
                    and_(
                        DemandeConge.date_fin >= debut_mois,
                        DemandeConge.date_fin <= fin_mois
                    ),
                    and_(
                        DemandeConge.date_debut <= debut_mois,
                        DemandeConge.date_fin >= fin_mois
                    )
                )
            )
        )
    
    result = await db.execute(query.order_by(DemandeConge.date_debut))
    demandes = result.scalars().all()
    
    print(demandes)
    # Enrichir avec les informations utilisateur
    enriched_demandes = []
    for demande in demandes:
        enriched = await enrich_demande_with_user_info(db, demande)
        enriched_demandes.append(enriched)
    
    return {
        "month": month,
        "year": year,
        "conges": enriched_demandes
    }

@router.get("/user/{user_id}", response_model=List[DemandeCongeRead])
async def get_demandes_by_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère les demandes d'un utilisateur spécifique avec contrôles de sécurité"""
    
    # Vérifier si l'utilisateur connecté peut voir les demandes de cet utilisateur
    can_view = False
    
    # 1. L'utilisateur peut voir ses propres demandes
    if current_user.id == user_id:
        can_view = True
    
    # 2. Les DRH peuvent voir toutes les demandes
    elif current_user.role == RoleEnum.DRH:
        can_view = True
    
    # 3. Les chefs de service peuvent voir les demandes de leur département
    elif current_user.role == RoleEnum.CHEF_SERVICE:
        # Vérifier si l'utilisateur cible est dans le même département
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        target_user = result.scalar_one_or_none()
        
        if target_user and target_user.departement_id == current_user.departement_id:
            can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas l'autorisation de voir les demandes de cet utilisateur"
        )
    
    # Récupérer les demandes de l'utilisateur
    result = await db.execute(
        select(DemandeConge)
        .where(DemandeConge.demandeur_id == user_id)
        .order_by(DemandeConge.date_demande.desc())
    )
    demandes = result.scalars().all()
    
    # Enrichir avec les informations utilisateur
    enriched_demandes = []
    for demande in demandes:
        enriched = await enrich_demande_with_user_info(db, demande)
        enriched_demandes.append(enriched)
    
    return enriched_demandes




 