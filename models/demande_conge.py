import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Date, Enum as SQLEnum, ForeignKey, Text, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .database import Base

class StatutDemandeEnum(str, Enum):
    EN_ATTENTE = "en_attente"
    APPROUVEE = "approuvee"
    REFUSEE = "refusee"
    ANNULEE = "annulee"
    DEMANDE_ANNULATION = "demande_annulation"  # Nouveau statut pour les demandes d'annulation
    ANNULATION_REFUSEE = "annulation_refusee"  # Nouveau statut quand l'annulation est refusée

class TypeCongeEnum(str, Enum):
    CONGES_PAYES = "conges_payes"
    CONGES_MALADIE = "conges_maladie"
    CONGES_MATERNITE = "conges_maternite"
    CONGES_PATERNITE = "conges_paternite"
    CONGES_SANS_SOLDE = "conges_sans_solde"
    RTT = "rtt"
    AUTRE = "autre"

class DemandeConge(Base):
    __tablename__ = "demandes_conges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    demandeur_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type_conge = Column(SQLEnum(TypeCongeEnum), nullable=False)
    date_debut = Column(Date, nullable=False)
    date_fin = Column(Date, nullable=False)
    nombre_jours = Column(String, nullable=True)  # Format "X jour(s) ouvrable(s) sur Y jour(s) total"
    working_time = Column(Integer, nullable=True)  # Nombre de jours ouvrables (int)
    real_time = Column(Integer, nullable=True)     # Nombre de jours réels/total (int)
    motif = Column(Text)
    statut = Column(SQLEnum(StatutDemandeEnum), default=StatutDemandeEnum.EN_ATTENTE)
    date_demande = Column(DateTime, default=datetime.utcnow)
    date_reponse = Column(DateTime, nullable=True)
    commentaire_validation = Column(Text)
    valideur_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Champs pour les demandes d'annulation
    demande_annulation = Column(Boolean, default=False)  # Indique si une annulation est demandée
    motif_annulation = Column(Text, nullable=True)  # Motif de la demande d'annulation
    date_demande_annulation = Column(DateTime, nullable=True)  # Date de la demande d'annulation
    # Champ pour l'attestation PDF
    attestation_pdf = Column(String, nullable=True)  # Nom du fichier PDF de l'attestation
    date_generation_attestation = Column(DateTime, nullable=True)  # Date de génération de l'attestation
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    demandeur = relationship("User", foreign_keys=[demandeur_id], overlaps="demandes_conges")
    valideur = relationship("User", foreign_keys=[valideur_id])

# Schéma pour les informations utilisateur de base
class UserBasicInfo(BaseModel):
    id: uuid.UUID
    nom: str
    prenom: str
    email: str
    role: Optional[str] = None
    departement: Optional[str] = None
    
    class Config:
        from_attributes = True

# Schémas Pydantic
class DemandeCongeBase(BaseModel):
    type_conge: TypeCongeEnum
    date_debut: date
    date_fin: date
    motif: Optional[str] = None

class DemandeCongeCreate(DemandeCongeBase):
    # nombre_jours, working_time et real_time seront calculés automatiquement côté backend
    pass

class DemandeCongeUpdate(BaseModel):
    type_conge: Optional[TypeCongeEnum] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    nombre_jours: Optional[str] = None
    working_time: Optional[int] = None
    real_time: Optional[int] = None
    motif: Optional[str] = None
    statut: Optional[StatutDemandeEnum] = None
    commentaire_validation: Optional[str] = None

class DemandeCongeRead(BaseModel):
    id: uuid.UUID
    demandeur_id: uuid.UUID
    type_conge: TypeCongeEnum
    date_debut: date
    date_fin: date
    nombre_jours: str
    working_time: int
    real_time: int
    motif: Optional[str] = None
    statut: StatutDemandeEnum
    date_demande: datetime
    date_reponse: Optional[datetime] = None
    commentaire_validation: Optional[str] = None
    valideur_id: Optional[uuid.UUID] = None
    # Champs pour les demandes d'annulation
    demande_annulation: Optional[bool] = None
    motif_annulation: Optional[str] = None
    date_demande_annulation: Optional[datetime] = None
    # Champs pour l'attestation PDF
    attestation_pdf: Optional[str] = None
    date_generation_attestation: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Informations utilisateur
    user: Optional[UserBasicInfo] = None
    valideur: Optional[UserBasicInfo] = None
    
    class Config:
        from_attributes = True

class DemandeCongeValidation(BaseModel):
    statut: StatutDemandeEnum
    commentaire_validation: Optional[str] = None

# Nouveau schéma pour les demandes d'annulation
class DemandeAnnulation(BaseModel):
    motif_annulation: str

# Nouveau schéma pour les actions dynamiques
class ActionDynamique(BaseModel):
    action: str
    label: str
    icon: Optional[str] = None
    color: Optional[str] = None

# Schéma enrichi avec les actions dynamiques
class DemandeCongeWithActions(DemandeCongeRead):
    actions: list[ActionDynamique] = [] 