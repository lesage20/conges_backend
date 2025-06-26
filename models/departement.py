import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .database import Base

class Departement(Base):
    __tablename__ = "departements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom = Column(String(100), nullable=False, unique=True)
    description = Column(String(500))
    chef_departement_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    budget_conges = Column(String, default="0")  # Budget en jours de congés
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    employes = relationship("User", back_populates="departement", foreign_keys="[User.departement_id]")

# Schémas Pydantic
class DepartementBase(BaseModel):
    nom: str
    description: Optional[str] = None
    chef_departement_id: Optional[uuid.UUID] = None
    budget_conges: str = "0"

class DepartementCreate(DepartementBase):
    pass

class DepartementUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    chef_departement_id: Optional[uuid.UUID] = None
    budget_conges: Optional[str] = None

class DepartementRead(DepartementBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True 