import uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase

DATABASE_URL = "sqlite+aiosqlite:///./conges.db"

# Création de l'engine asynchrone
engine = create_async_engine(DATABASE_URL, echo=True)

# Session maker asynchrone
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base pour tous les modèles
class Base(DeclarativeBase):
    pass

# Fonction pour obtenir l'URL de la base de données
def get_database_url() -> str:
    return DATABASE_URL

# Fonction pour obtenir une session de base de données
async def get_database() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

# Fonction pour obtenir le database adapter pour FastAPIUsers
async def get_user_db():
    async for session in get_database():
        from .user import User
        yield SQLAlchemyUserDatabase(session, User) 