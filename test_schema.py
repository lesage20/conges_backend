#!/usr/bin/env python3
"""
Script de test pour vérifier les schémas Pydantic avec la nouvelle structure
"""

import asyncio
import sys
from pathlib import Path
from datetime import date

# Ajouter le répertoire parent (backend) au PYTHONPATH
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.database import async_session_maker
from models.user import User, UserRead
from sqlalchemy import select

async def test_schema():
    """Teste la sérialisation des utilisateurs avec les nouveaux schémas"""
    
    async with async_session_maker() as session:
        # Récupérer un utilisateur
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if user:
            print("🧪 Test de sérialisation avec le nouveau schéma UserRead")
            print("=" * 60)
            
            # Test de sérialisation avec Pydantic
            try:
                user_data = UserRead.model_validate(user)
                print("✅ Sérialisation réussie!")
                print(f"   📧 Email: {user_data.email}")
                print(f"   👤 Nom complet: {user_data.nom_complet}")
                print(f"   📅 Date embauche: {user_data.date_embauche} (type: {type(user_data.date_embauche)})")
                print(f"   🏖️  Solde congés: {user_data.solde_conges} jours (type: {type(user_data.solde_conges)})")
                print(f"   🎯 Rôle: {user_data.role}")
                
                # Test de conversion en dict JSON
                dict_data = user_data.model_dump()
                print("\n📋 Données JSON:")
                import json
                print(json.dumps(dict_data, indent=2, default=str))
                
            except Exception as e:
                print(f"❌ Erreur de sérialisation: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ Aucun utilisateur trouvé en base")

if __name__ == "__main__":
    asyncio.run(test_schema()) 