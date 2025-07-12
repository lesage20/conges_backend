import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .database import Base

class TypeNotificationEnum(str, Enum):
    NOUVELLE_DEMANDE = "nouvelle_demande"
    DEMANDE_APPROUVEE = "demande_approuvee"
    DEMANDE_REFUSEE = "demande_refusee"
    RAPPEL_RETOUR_CONGE = "rappel_retour_conge"
    RAPPEL_15_JOURS = "rappel_15_jours"
    DEMANDE_ANNULATION = "demande_annulation"
    ANNULATION_APPROUVEE = "annulation_approuvee"
    ANNULATION_REFUSEE = "annulation_refusee"
    ALERTE_CONFLIT_EQUIPE = "alerte_conflit_equipe"

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destinataire_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type_notification = Column(SQLEnum(TypeNotificationEnum), nullable=False)
    titre = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    demande_conge_id = Column(UUID(as_uuid=True), ForeignKey("demandes_conges.id"), nullable=True)
    lue = Column(Boolean, default=False)
    email_envoye = Column(Boolean, default=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_lecture = Column(DateTime, nullable=True)
    date_envoi_email = Column(DateTime, nullable=True)
    
    # Relations
    destinataire = relationship("User", foreign_keys=[destinataire_id])
    demande_conge = relationship("DemandeConge", foreign_keys=[demande_conge_id])

# Modèles Pydantic pour l'API
class NotificationRead(BaseModel):
    id: uuid.UUID
    destinataire_id: uuid.UUID
    type_notification: TypeNotificationEnum
    titre: str
    message: str
    demande_conge_id: Optional[uuid.UUID] = None
    lue: bool
    email_envoye: bool
    date_creation: datetime
    date_lecture: Optional[datetime] = None
    date_envoi_email: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationCreate(BaseModel):
    destinataire_id: uuid.UUID
    type_notification: TypeNotificationEnum
    titre: str
    message: str
    demande_conge_id: Optional[uuid.UUID] = None

class NotificationUpdate(BaseModel):
    lue: Optional[bool] = None
    date_lecture: Optional[datetime] = None

# Règles pour les notifications automatiques
REGLES_NOTIFICATIONS = {
    # Notifications immédiates lors de changements de statut
    "nouvelle_demande": {
        "destinataires": ["chef_service", "drh"],
        "titre": "Nouvelle demande de congé",
        "template": "Une nouvelle demande de congé a été soumise par {demandeur}"
    },
    "demande_approuvee": {
        "destinataires": ["demandeur"],
        "titre": "Demande approuvée",
        "template": "Votre demande de congé du {date_debut} au {date_fin} a été approuvée"
    },
    "demande_refusee": {
        "destinataires": ["demandeur"],
        "titre": "Demande refusée",
        "template": "Votre demande de congé du {date_debut} au {date_fin} a été refusée"
    },
    
    # Notifications automatiques avec délai
    "rappel_15_jours": {
        "destinataires": ["demandeur", "chef_service"],
        "titre": "Rappel : Congé dans 15 jours",
        "template": "Rappel : Le congé de {demandeur} commence dans 15 jours ({date_debut})",
        "delai_jours": -15  # 15 jours avant la date de début
    },
    "rappel_retour_conge": {
        "destinataires": ["demandeur", "chef_service"],
        "titre": "Rappel : Retour de congé",
        "template": "Rappel : {demandeur} reprend le travail demain après son congé",
        "delai_jours": 1  # 1 jour après la date de fin
    }
} 