#!/usr/bin/env python3
"""
Script pour recréer la base de données avec la nouvelle structure
"""

import asyncio
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent (backend) au PYTHONPATH
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.database import Base, engine

async def recreate_database():
    """Recrée la base de données en supprimant toutes les tables"""
    
    print("🗑️ Suppression des anciennes tables...")
    
    # Supprimer toutes les tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("✅ Tables supprimées")
        
        # Recréer toutes les tables avec la nouvelle structure
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Nouvelles tables créées")
    
    print("🎉 Base de données recréée avec succès!")

if __name__ == "__main__":
    print("🔄 Recréation de la base de données...")
    asyncio.run(recreate_database())
    print("✅ Terminé!") 