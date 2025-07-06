import sys
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

# Ajouter le répertoire courant au PYTHONPATH
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from models.database import Base, engine
from routes import auth_router, users_router, departements_router, demandes_conges_router
from middlewares.logging_middleware import LoggingMiddleware
from middlewares.error_handling import setup_error_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Créer les tables au démarrage
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Créer le dossier attestations s'il n'existe pas
    attestations_dir = Path("attestations")
    attestations_dir.mkdir(exist_ok=True)
    
    yield
    # Cleanup au shutdown (si nécessaire)

# Création de l'application FastAPI
app = FastAPI(
    title="API Gestion des Congés",
    description="API pour la gestion des congés avec authentification et rôles",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # URLs du frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de logging
app.add_middleware(LoggingMiddleware)

# Configuration des gestionnaires d'erreurs
setup_error_handlers(app)

# Inclusion des routers
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(departements_router, prefix="/api")
app.include_router(demandes_conges_router, prefix="/api")

# Configuration des fichiers statiques pour les attestations
app.mount("/attestations", StaticFiles(directory="attestations"), name="attestations")

@app.get("/")
async def root():
    """Endpoint de test"""
    return {"message": "API Gestion des Congés - Version 1.0.0"}

@app.get("/health")
async def health_check():
    """Endpoint de santé pour les monitoring"""
    return {"status": "healthy", "service": "conges-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
