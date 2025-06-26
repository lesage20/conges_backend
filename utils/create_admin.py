import asyncio
import sys
import uuid
from pathlib import Path
from datetime import date

# Ajouter le répertoire parent (backend) au PYTHONPATH
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from models.database import async_session_maker, Base, engine
from models.user import User, RoleEnum
from models.departement import Departement
from fastapi_users.password import PasswordHelper

async def create_admin_user():
    """Crée un utilisateur administrateur initial"""
    
    # Créer les tables si elles n'existent pas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session_maker() as session:
        # Créer un département DRH
        departement_drh = Departement(
            nom="Direction des Ressources Humaines",
            description="Département en charge de la gestion RH",
            budget_conges="365"
        )
        session.add(departement_drh)
        await session.commit()
        await session.refresh(departement_drh)
        
        # Vérifier si l'admin existe déjà
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "admin@company.com")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print("ERREUR: L'utilisateur admin existe déjà!")
            return
        
        # Créer l'utilisateur admin
        password_helper = PasswordHelper()
        hashed_password = password_helper.hash("admin123")
        
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@company.com",
            hashed_password=hashed_password,
            nom="Admin",
            prenom="Système",
            telephone="+33123456789",
            numero_piece_identite="ADMIN123456789",
            poste="Directeur RH",
            role=RoleEnum.DRH,
            date_embauche=date(2020, 1, 15),  # Date d'embauche ancienne pour avoir tous les congés
            departement_id=departement_drh.id,
            is_active=True,
            is_superuser=True,
            is_verified=True
        )
        
        session.add(admin_user)
        await session.commit()
        
        print("SUCCESS: Utilisateur administrateur créé avec succès!")
        print("Email: admin@company.com")
        print("Mot de passe: admin123")
        print("Département: Direction des Ressources Humaines")

async def create_sample_data():
    """Crée des données d'exemple pour les tests"""
    
    async with async_session_maker() as session:
        from sqlalchemy import select
        
        # Créer quelques départements d'exemple
        departements = [
            {
                "nom": "Développement",
                "description": "Équipe de développement logiciel",
                "budget_conges": "300"
            },
            {
                "nom": "Marketing",
                "description": "Équipe marketing et communication",
                "budget_conges": "250"
            },
            {
                "nom": "Ventes",
                "description": "Équipe commerciale",
                "budget_conges": "280"
            }
        ]
        
        for dept_data in departements:
            # Vérifier si le département existe déjà
            result = await session.execute(
                select(Departement).where(Departement.nom == dept_data["nom"])
            )
            existing_dept = result.scalar_one_or_none()
            
            if not existing_dept:
                dept = Departement(**dept_data)
                session.add(dept)
        
        await session.commit()
        print("SUCCESS: Départements d'exemple créés!")
        
        # Créer quelques utilisateurs d'exemple
        password_helper = PasswordHelper()
        
        # Récupérer les départements
        result = await session.execute(select(Departement))
        departements_list = result.scalars().all()
        
        sample_users = [
            {
                "email": "chef.dev@company.com",
                "password": "chef123",
                "nom": "Martin",
                "prenom": "Jean",
                "telephone": "+33123456790",
                "numero_piece_identite": "DEV123456789",
                "poste": "Chef d'équipe Développement",
                "role": RoleEnum.CHEF_SERVICE,
                "date_embauche": date(2022, 3, 15),  # Plus de 24 mois -> 27 jours
                "departement": "Développement"
            },
            {
                "email": "dev1@company.com", 
                "password": "dev123",
                "nom": "Dupont",
                "prenom": "Marie",
                "telephone": "+33123456791",
                "numero_piece_identite": "EMP123456789",
                "poste": "Développeuse Senior",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2024, 6, 1),  # Récent -> calcul prorata
                "departement": "Développement"
            },
            {
                "email": "marketing@company.com",
                "password": "marketing123", 
                "nom": "Bernard",
                "prenom": "Sophie",
                "telephone": "+33123456792",
                "numero_piece_identite": "MKT123456789",
                "poste": "Responsable Marketing",
                "role": RoleEnum.CHEF_SERVICE,
                "date_embauche": date(2023, 1, 5),  # 1 an au 10 janvier -> 27 jours
                "departement": "Marketing"
            }
        ]
        
        for user_data in sample_users:
            # Vérifier si l'utilisateur existe déjà
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                # Trouver le département
                dept = next((d for d in departements_list if d.nom == user_data["departement"]), None)
                
                user = User(
                    id=uuid.uuid4(),
                    email=user_data["email"],
                    hashed_password=password_helper.hash(user_data["password"]),
                    nom=user_data["nom"],
                    prenom=user_data["prenom"],
                    telephone=user_data["telephone"],
                    numero_piece_identite=user_data["numero_piece_identite"],
                    poste=user_data["poste"],
                    role=user_data["role"],
                    date_embauche=user_data["date_embauche"],
                    departement_id=dept.id if dept else None,
                    is_active=True,
                    is_verified=True
                )
                
                session.add(user)
        
        await session.commit()
        print("SUCCESS: Utilisateurs d'exemple créés!")

if __name__ == "__main__":
    print("INIT: Création de l'utilisateur administrateur et des données d'exemple...")
    asyncio.run(create_admin_user())
    asyncio.run(create_sample_data())
    print("SUCCESS: Initialisation terminée!") 