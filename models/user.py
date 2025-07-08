import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional
import math

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users import schemas
from sqlalchemy import Column, String, Boolean, DateTime, Date, Integer, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .database import Base

class RoleEnum(str, Enum):
    EMPLOYE = "employe"
    CHEF_SERVICE = "chef_service"
    DRH = "drh"

class GenreEnum(str, Enum):
    HOMME = "homme"
    FEMME = "femme"

def validate_anciennete_minimum(date_embauche: date) -> bool:
    """
    Valide qu'un employé a au moins 1 an d'ancienneté au 10 janvier de l'année courante.
    
    Args:
        date_embauche: Date d'embauche de l'employé
        
    Returns:
        bool: True si l'employé a au moins 1 an d'ancienneté au 10 janvier, False sinon
    """
    if not date_embauche:
        return False
    
    annee_courante = date.today().year
    date_10_janvier_courante = date(annee_courante, 1, 10)
    
    # Calculer la différence en jours et convertir en années
    anciennete_jours = (date_10_janvier_courante - date_embauche).days
    anciennete_ans = anciennete_jours / 365
    
    return anciennete_ans >= 1

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
    
    # Nouveaux champs ajoutés
    date_naissance = Column(Date, nullable=True)
    nombre_enfants = Column(Integer, default=0)
    has_medaille_honneur = Column(Boolean, default=False)
    genre = Column(SQLEnum(GenreEnum), nullable=True)
    
    # Relations
    departement = relationship("Departement", back_populates="employes", foreign_keys=[departement_id])
    demandes_conges = relationship("DemandeConge", foreign_keys="[DemandeConge.demandeur_id]")
    
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
        jours_conges = 0
        # Calculer la date du 10 janvier de l'année courante
        annee_courante = aujourd_hui.year
        date_10_janvier_precedent = date(annee_courante, 1, 10)
        
        # Vérifier si l'employé a au moins 24 mois d'ancienneté
        anciennete_mois = (date_10_janvier_precedent - date_embauche).days // 30
        if anciennete_mois >= 24:
            # Plus de 24 mois : 12 * 2.2 = 26.4 jours
            jours_conges = math.ceil(12 * 2.2)
        
        # Vérifier si l'employé a 1 an ou plus au 10 janvier précédent
        elif  12 <= anciennete_mois < 24:
            # 1 an ou plus au 10 janvier : 12 * 2.2 = 26.4 jours
            jours_conges = math.ceil(anciennete_mois * 2.2)
        else:
            jours_conges = 0
        
        anciennete_ans = (date_10_janvier_precedent - date_embauche).days // 365
        if anciennete_ans >= 30:
            jours_conges += 8
        elif anciennete_ans >= 25:
            jours_conges += 7
        elif anciennete_ans >= 20:
            jours_conges += 5
        elif anciennete_ans >= 15:
            jours_conges += 3
        elif anciennete_ans >= 10:
            jours_conges += 2
        elif anciennete_ans >= 5:
            jours_conges += 1

        if self.genre and self.genre.lower() == "femme" and self.date_naissance:
            age = (date_10_janvier_precedent - self.date_naissance).days // 365
            if age < 21:
                jours_conges += 2 * self.nombre_enfants
            else:
                jours_conges += 2 * (self.nombre_enfants - 3) if self.nombre_enfants >= 4 else 0
        
        if self.has_medaille_honneur:
            jours_conges += 1
        
        
        return jours_conges

    @property
    def solde_conges_restant(self):
        """Calcule le solde de congés restant en soustrayant les jours pris des demandes approuvées"""
        from .demande_conge import StatutDemandeEnum
        
        solde_total = self.solde_conges
        
        # Calculer les jours pris (demandes approuvées uniquement)
        jours_pris = 0
        for demande in self.demandes_conges:
            if demande.statut == StatutDemandeEnum.APPROUVEE:
                jours_pris += demande.working_time or 0
        
        return max(0, solde_total - jours_pris)  # Ne pas retourner une valeur négative

    def calculate_solde_conges_restant(self, demandes_conges=None):
        """Calcule le solde de congés restant avec une liste de demandes fournie"""
        from .demande_conge import StatutDemandeEnum
        
        solde_total = self.solde_conges
        
        # Calculer les jours pris (demandes approuvées uniquement)
        jours_pris = 0
        if demandes_conges:
            for demande in demandes_conges:
                if demande.statut == StatutDemandeEnum.APPROUVEE:
                    jours_pris += demande.working_time or 0
        
        return max(0, solde_total - jours_pris)  # Ne pas retourner une valeur négative

    
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
    solde_conges_restant: int  # Calculé automatiquement
    departement_id: Optional[uuid.UUID] = None
    nom_complet: str
    date_naissance: Optional[date] = None
    nombre_enfants: int = 0
    has_medaille_honneur: bool = False
    genre: Optional[GenreEnum] = None

class UserCreate(schemas.BaseUserCreate):
    nom: str
    prenom: str
    telephone: str
    numero_piece_identite: str
    poste: Optional[str] = None
    role: RoleEnum = RoleEnum.EMPLOYE
    date_embauche: date  # Date seulement
    departement_id: Optional[uuid.UUID] = None
    date_naissance: Optional[date] = None
    nombre_enfants: int = 0
    has_medaille_honneur: bool = False
    genre: Optional[GenreEnum] = None

class UserUpdate(schemas.BaseUserUpdate):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None
    numero_piece_identite: Optional[str] = None
    poste: Optional[str] = None
    role: Optional[RoleEnum] = None
    date_embauche: Optional[date] = None  # Date seulement
    departement_id: Optional[uuid.UUID] = None
    date_naissance: Optional[date] = None
    nombre_enfants: Optional[int] = None
    has_medaille_honneur: Optional[bool] = None
    genre: Optional[GenreEnum] = None 