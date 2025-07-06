import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Date, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .database import Base

class StatutDemandeEnum(str, Enum):
    EN_ATTENTE = "en_attente"
    APPROUVEE = "approuvee"
    REFUSEE = "refusee"
    ANNULEE = "annulee"

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
    nombre_jours = Column(String, nullable=True)
    motif = Column(Text)
    statut = Column(SQLEnum(StatutDemandeEnum), default=StatutDemandeEnum.EN_ATTENTE)
    date_demande = Column(DateTime, default=datetime.utcnow)
    date_reponse = Column(DateTime, nullable=True)
    commentaire_validation = Column(Text)
    valideur_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    demandeur = relationship("User", foreign_keys=[demandeur_id], back_populates="demandes_conges")
    valideur = relationship("User", foreign_keys=[valideur_id])

# Schémas Pydantic
class DemandeCongeBase(BaseModel):
    type_conge: TypeCongeEnum
    date_debut: date
    date_fin: date
    nombre_jours: str
    motif: Optional[str] = None

class DemandeCongeCreate(DemandeCongeBase):
    pass

class DemandeCongeUpdate(BaseModel):
    type_conge: Optional[TypeCongeEnum] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    nombre_jours: Optional[str] = None
    motif: Optional[str] = None
    statut: Optional[StatutDemandeEnum] = None
    commentaire_validation: Optional[str] = None

class DemandeCongeRead(DemandeCongeBase):
    id: uuid.UUID
    demandeur_id: uuid.UUID
    statut: StatutDemandeEnum
    date_demande: datetime
    date_reponse: Optional[datetime] = None
    commentaire_validation: Optional[str] = None
    valideur_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DemandeCongeValidation(BaseModel):
    statut: StatutDemandeEnum
    commentaire_validation: Optional[str] = None 