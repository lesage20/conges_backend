#!/usr/bin/env python3
"""
Service de notifications pour la gestion automatique des notifications de congés
"""

import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.notification import (
    Notification, NotificationCreate, TypeNotificationEnum, REGLES_NOTIFICATIONS
)
from models.demande_conge import DemandeConge, StatutDemandeEnum
from models.user import User, RoleEnum

class NotificationService:
    """Service pour gérer les notifications automatiques"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def creer_notification(
        self, 
        destinataire_id: uuid.UUID,
        type_notification: TypeNotificationEnum,
        titre: str,
        message: str,
        demande_conge_id: Optional[uuid.UUID] = None
    ) -> Notification:
        """Crée une nouvelle notification"""
        notification = Notification(
            destinataire_id=destinataire_id,
            type_notification=type_notification,
            titre=titre,
            message=message,
            demande_conge_id=demande_conge_id
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification
    
    async def notifier_nouvelle_demande(self, demande: DemandeConge) -> List[Notification]:
        """Notifie les responsables d'une nouvelle demande de congé"""
        notifications = []
        
        # Récupérer les informations du demandeur
        demandeur = await self._get_user(demande.demandeur_id)
        if not demandeur:
            return notifications
        
        # Déterminer les destinataires selon les règles
        destinataires = await self._get_destinataires_pour_nouvelle_demande(demandeur)
        
        # Créer le message
        titre = "Nouvelle demande de congé"
        message = f"Une nouvelle demande de congé a été soumise par {demandeur.nom_complet} du {demande.date_debut.strftime('%d/%m/%Y')} au {demande.date_fin.strftime('%d/%m/%Y')}"
        
        # Créer les notifications
        for destinataire_id in destinataires:
            notification = await self.creer_notification(
                destinataire_id=destinataire_id,
                type_notification=TypeNotificationEnum.NOUVELLE_DEMANDE,
                titre=titre,
                message=message,
                demande_conge_id=demande.id
            )
            notifications.append(notification)
        
        return notifications
    
    async def notifier_validation_demande(
        self, 
        demande: DemandeConge, 
        approuvee: bool,
        commentaire: Optional[str] = None
    ) -> List[Notification]:
        """Notifie le demandeur de la validation de sa demande"""
        notifications = []
        
        # Récupérer les informations du demandeur
        demandeur = await self._get_user(demande.demandeur_id)
        if not demandeur:
            return notifications
        
        # Déterminer le type et le message
        if approuvee:
            type_notif = TypeNotificationEnum.DEMANDE_APPROUVEE
            titre = "Demande approuvée"
            message = f"Votre demande de congé du {demande.date_debut.strftime('%d/%m/%Y')} au {demande.date_fin.strftime('%d/%m/%Y')} a été approuvée"
        else:
            type_notif = TypeNotificationEnum.DEMANDE_REFUSEE
            titre = "Demande refusée"
            message = f"Votre demande de congé du {demande.date_debut.strftime('%d/%m/%Y')} au {demande.date_fin.strftime('%d/%m/%Y')} a été refusée"
        
        if commentaire:
            message += f"\n\nCommentaire : {commentaire}"
        
        # Créer la notification
        notification = await self.creer_notification(
            destinataire_id=demande.demandeur_id,
            type_notification=type_notif,
            titre=titre,
            message=message,
            demande_conge_id=demande.id
        )
        notifications.append(notification)
        
        return notifications
    
    async def generer_rappels_automatiques(self) -> List[Notification]:
        """Génère les rappels automatiques (15 jours avant et retour de congé)"""
        notifications = []
        
        # Date d'aujourd'hui
        aujourd_hui = date.today()
        
        # Rappels 15 jours avant le début du congé
        date_debut_cible = aujourd_hui + timedelta(days=15)
        notifications_15j = await self._generer_rappels_15_jours(date_debut_cible)
        notifications.extend(notifications_15j)
        
        # Rappels de retour de congé (le jour après la fin du congé)
        date_fin_cible = aujourd_hui - timedelta(days=1)
        notifications_retour = await self._generer_rappels_retour(date_fin_cible)
        notifications.extend(notifications_retour)
        
        return notifications
    
    async def _generer_rappels_15_jours(self, date_debut: date) -> List[Notification]:
        """Génère les rappels 15 jours avant le début du congé"""
        notifications = []
        
        # Trouver les demandes approuvées qui commencent dans 15 jours
        result = await self.db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                    DemandeConge.date_debut == date_debut
                )
            )
        )
        demandes = result.scalars().all()
        
        for demande in demandes:
            # Vérifier qu'on n'a pas déjà envoyé ce rappel
            if await self._notification_deja_envoyee(demande.id, TypeNotificationEnum.RAPPEL_15_JOURS):
                continue
            
            demandeur = await self._get_user(demande.demandeur_id)
            if not demandeur:
                continue
            
            # Destinataires : demandeur + chef de service
            destinataires = [demande.demandeur_id]
            if demandeur.departement_id:
                chef_service = await self._get_chef_service(demandeur.departement_id)
                if chef_service and chef_service.id != demande.demandeur_id:
                    destinataires.append(chef_service.id)
            
            # Créer les notifications
            titre = "Rappel : Congé dans 15 jours"
            message = f"Rappel : Le congé de {demandeur.nom_complet} commence dans 15 jours ({demande.date_debut.strftime('%d/%m/%Y')})"
            
            for destinataire_id in destinataires:
                notification = await self.creer_notification(
                    destinataire_id=destinataire_id,
                    type_notification=TypeNotificationEnum.RAPPEL_15_JOURS,
                    titre=titre,
                    message=message,
                    demande_conge_id=demande.id
                )
                notifications.append(notification)
        
        return notifications
    
    async def _generer_rappels_retour(self, date_fin: date) -> List[Notification]:
        """Génère les rappels de retour de congé"""
        notifications = []
        
        # Trouver les demandes approuvées qui se terminent hier (retour aujourd'hui)
        result = await self.db.execute(
            select(DemandeConge).where(
                and_(
                    DemandeConge.statut == StatutDemandeEnum.APPROUVEE,
                    DemandeConge.date_fin == date_fin
                )
            )
        )
        demandes = result.scalars().all()
        
        for demande in demandes:
            # Vérifier qu'on n'a pas déjà envoyé ce rappel
            if await self._notification_deja_envoyee(demande.id, TypeNotificationEnum.RAPPEL_RETOUR_CONGE):
                continue
            
            demandeur = await self._get_user(demande.demandeur_id)
            if not demandeur:
                continue
            
            # Destinataires : chef de service uniquement (le demandeur sait qu'il revient)
            destinataires = []
            if demandeur.departement_id:
                chef_service = await self._get_chef_service(demandeur.departement_id)
                if chef_service and chef_service.id != demande.demandeur_id:
                    destinataires.append(chef_service.id)
            
            # Créer les notifications
            titre = "Rappel : Retour de congé"
            message = f"Rappel : {demandeur.nom_complet} reprend le travail aujourd'hui après son congé"
            
            for destinataire_id in destinataires:
                notification = await self.creer_notification(
                    destinataire_id=destinataire_id,
                    type_notification=TypeNotificationEnum.RAPPEL_RETOUR_CONGE,
                    titre=titre,
                    message=message,
                    demande_conge_id=demande.id
                )
                notifications.append(notification)
        
        return notifications
    
    async def _get_destinataires_pour_nouvelle_demande(self, demandeur: User) -> List[uuid.UUID]:
        """Détermine les destinataires pour une nouvelle demande selon les règles métier"""
        destinataires = []
        
        # Chef de service du département (s'il y en a un)
        if demandeur.departement_id:
            chef_service = await self._get_chef_service(demandeur.departement_id)
            if chef_service and chef_service.id != demandeur.id:
                destinataires.append(chef_service.id)
        
        # DRH (tous les DRH)
        drh_result = await self.db.execute(
            select(User).where(User.role == RoleEnum.DRH)
        )
        drh_users = drh_result.scalars().all()
        for drh in drh_users:
            if drh.id not in destinataires and drh.id != demandeur.id:
                destinataires.append(drh.id)
        
        return destinataires
    
    async def _get_user(self, user_id: uuid.UUID) -> Optional[User]:
        """Récupère un utilisateur par son ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_chef_service(self, departement_id: uuid.UUID) -> Optional[User]:
        """Récupère le chef de service d'un département"""
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.departement_id == departement_id,
                    User.role == RoleEnum.CHEF_SERVICE
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _notification_deja_envoyee(
        self, 
        demande_id: uuid.UUID, 
        type_notification: TypeNotificationEnum
    ) -> bool:
        """Vérifie si une notification du type donné a déjà été envoyée pour cette demande"""
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.demande_conge_id == demande_id,
                    Notification.type_notification == type_notification
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def marquer_comme_lue(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Marque une notification comme lue"""
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.destinataire_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            return False
        
        notification.lue = True
        notification.date_lecture = datetime.utcnow()
        await self.db.commit()
        return True
    
    async def get_notifications_utilisateur(
        self, 
        user_id: uuid.UUID, 
        non_lues_seulement: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Récupère les notifications d'un utilisateur"""
        query = select(Notification).where(Notification.destinataire_id == user_id)
        
        if non_lues_seulement:
            query = query.where(Notification.lue == False)
        
        query = query.order_by(Notification.date_creation.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all() 