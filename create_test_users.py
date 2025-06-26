#!/usr/bin/env python3
"""
Script pour créer des utilisateurs de test dans la base de données
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire courant au PYTHONPATH
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from models.database import async_session_maker
from models.user import User, RoleEnum
from models.departement import Departement
from fastapi_users.password import PasswordHelper
from datetime import date
import uuid

async def create_test_users():
    """Créer des utilisateurs de test"""
    
    password_helper = PasswordHelper()
    
    # Utilisateurs de test
    test_users = [
        {
            "email": "drh@example.com",
            "password": "password",
            "nom": "Directrice",
            "prenom": "Marie",
            "telephone": "01.23.45.67.89",
            "numero_piece_identite": "DRH123456",
            "poste": "Directrice des Ressources Humaines",
            "role": RoleEnum.DRH,
        },
        {
            "email": "chef@example.com", 
            "password": "password",
            "nom": "Chef",
            "prenom": "Pierre",
            "telephone": "01.23.45.67.90",
            "numero_piece_identite": "CHS123456",
            "poste": "Chef de Service IT",
            "role": RoleEnum.CHEF_SERVICE,
        },
        {
            "email": "employe@example.com",
            "password": "password", 
            "nom": "Employé",
            "prenom": "Jean",
            "telephone": "01.23.45.67.91",
            "numero_piece_identite": "EMP123456",
            "poste": "Développeur",
            "role": RoleEnum.EMPLOYE,
        }
    ]
    
    async with async_session_maker() as session:
        try:
            # Créer ou récupérer des départements
            dept_it = Departement(
                id=uuid.uuid4(),
                nom="Informatique",
                description="Département informatique"
            )
            dept_rh = Departement(
                id=uuid.uuid4(),
                nom="Ressources Humaines", 
                description="Département des ressources humaines"
            )
            
            session.add(dept_it)
            session.add(dept_rh)
            await session.commit()
            
            print("Départements créés:")
            print(f"- IT: {dept_it.id}")
            print(f"- RH: {dept_rh.id}")
            
            # Créer les utilisateurs
            for user_data in test_users:
                # Vérifier si l'utilisateur existe déjà
                existing_user = await session.get(User, {"email": user_data["email"]})
                if existing_user:
                    print(f"L'utilisateur {user_data['email']} existe déjà.")
                    continue
                
                # Hacher le mot de passe
                hashed_password = password_helper.hash(user_data["password"])
                
                # Assigner département selon le rôle
                departement_id = dept_rh.id if user_data["role"] == RoleEnum.DRH else dept_it.id
                
                # Créer l'utilisateur
                user = User(
                    id=uuid.uuid4(),
                    email=user_data["email"],
                    hashed_password=hashed_password,
                    nom=user_data["nom"],
                    prenom=user_data["prenom"],
                    telephone=user_data["telephone"],
                    numero_piece_identite=user_data["numero_piece_identite"],
                    poste=user_data["poste"],
                    role=user_data["role"],
                    date_embauche=date.today(),
                    departement_id=departement_id,
                    is_active=True,
                    is_verified=True,
                    is_superuser=user_data["role"] == RoleEnum.DRH
                )
                
                session.add(user)
                print(f"Utilisateur créé: {user.email} ({user.role.value})")
            
            await session.commit()
            print("\n✅ Tous les utilisateurs de test ont été créés avec succès!")
            
            print("\n📋 Comptes de test:")
            print("Email: drh@example.com | Mot de passe: password | Rôle: DRH")
            print("Email: chef@example.com | Mot de passe: password | Rôle: Chef de Service")
            print("Email: employe@example.com | Mot de passe: password | Rôle: Employé")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Erreur lors de la création des utilisateurs: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(create_test_users()) 