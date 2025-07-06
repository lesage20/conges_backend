import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional
import math

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users import schemas
from sqlalchemy import Column, String, Boolean, DateTime, Date, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .database import Base

class RoleEnum(str, Enum):
    EMPLOYE = "employe"
    CHEF_SERVICE = "chef_service"
    DRH = "drh"

class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"
    
    # Champs FastAPIUsers hérités : id, email, hashed_password, is_active, is_superuser, is_verified
    
    # Champs personnalisés
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    telephone = Column(String(20), nullable=False)
    numero_piece_identite = Column(String(50), nullable=False, unique=True)
    poste = Column(String(100), nullable=True)  # Facultatif
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.EMPLOYE)
    date_embauche = Column(Date, default=date.today)  # Date seulement, pas datetime
    departement_id = Column(UUID(as_uuid=True), ForeignKey("departements.id"), nullable=True)
    
    # Relations
    departement = relationship("Departement", back_populates="employes", foreign_keys=[departement_id])
    demandes_conges = relationship("DemandeConge", back_populates="demandeur", foreign_keys="[DemandeConge.demandeur_id]")
    
    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"
    
    @property
    def solde_conges(self):
        """Calcule automatiquement le solde de congés selon les critères d'ancienneté"""
        if not self.date_embauche:
            return 0  # Valeur par défaut
        
        aujourd_hui = date.today()
        date_embauche = self.date_embauche
        
        # Calculer la date du 10 janvier de l'année précédente
        annee_courante = aujourd_hui.year
        date_10_janvier_precedent = date(annee_courante - 1, 1, 10)
        
        # Vérifier si l'employé a au moins 24 mois d'ancienneté
        anciennete_mois = (aujourd_hui.year - date_embauche.year) * 12 + (aujourd_hui.month - date_embauche.month)
        if anciennete_mois >= 24:
            # Plus de 24 mois : 12 * 2.2 = 26.4 jours
            return math.ceil(12 * 2.2)
        
        # Vérifier si l'employé a 1 an ou plus au 10 janvier précédent
        if date_embauche <= date_10_janvier_precedent:
            # 1 an ou plus au 10 janvier : 12 * 2.2 = 26.4 jours
            return math.ceil(12 * 2.2)
        
        # Moins d'un an au 10 janvier précédent : calcul prorata
        # Nombre de jours depuis l'embauche
        jours_travailles = (aujourd_hui - date_embauche).days
        # Convertir en mois approximatifs et multiplier par 2.2
        mois_travailles = jours_travailles / 30.0  # Approximation
        conges_calcules = mois_travailles * 2.2
        
        return math.ceil(conges_calcules)
    
    @property
    def manager(self):
        """Retourne le manager (chef de service du département)"""
        if self.departement and self.role != RoleEnum.CHEF_SERVICE:
            # Rechercher le chef de service dans le même département
            from sqlalchemy.orm import Session
            # Cette méthode sera utilisée dans les services, pas directement ici
            return None
        return None

# Schémas Pydantic pour FastAPIUsers
class UserRead(schemas.BaseUser[uuid.UUID]):
    nom: str
    prenom: str
    telephone: str
    numero_piece_identite: str
    poste: Optional[str] = None
    role: RoleEnum
    date_embauche: date  # Date seulement
    solde_conges: int  # Calculé automatiquement
    departement_id: Optional[uuid.UUID] = None
    nom_complet: str

class UserCreate(schemas.BaseUserCreate):
    nom: str
    prenom: str
    telephone: str
    numero_piece_identite: str
    poste: Optional[str] = None
    role: RoleEnum = RoleEnum.EMPLOYE
    date_embauche: date  # Date seulement
    departement_id: Optional[uuid.UUID] = None

class UserUpdate(schemas.BaseUserUpdate):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None
    numero_piece_identite: Optional[str] = None
    poste: Optional[str] = None
    role: Optional[RoleEnum] = None
    date_embauche: Optional[date] = None  # Date seulement
    departement_id: Optional[uuid.UUID] = None 