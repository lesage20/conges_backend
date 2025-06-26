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
            email="drh@entreprise.com",
            hashed_password=hashed_password,
            nom="Dubois",
            prenom="Caroline",
            telephone="+33123456789",
            numero_piece_identite="DRH123456789",
            poste="Directrice des Ressources Humaines",
            role=RoleEnum.DRH,
            date_embauche=date(2018, 9, 1),  # Plus de 5 ans d'ancienneté
            departement_id=departement_drh.id,
            is_active=True,
            is_superuser=True,
            is_verified=True
        )
        
        session.add(admin_user)
        await session.commit()
        
        print("SUCCESS: Utilisateur administrateur créé avec succès!")
        print("Email: drh@entreprise.com")
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
        
        # Données plus réalistes avec plusieurs employés par département
        sample_users = [
            # === DÉPARTEMENT DÉVELOPPEMENT ===
            {
                "email": "chef.dev@entreprise.com",
                "password": "chef123",
                "nom": "Laurent",
                "prenom": "Thomas",
                "telephone": "+33123456790",
                "numero_piece_identite": "CHEF001",
                "poste": "Chef d'équipe Développement",
                "role": RoleEnum.CHEF_SERVICE,
                "date_embauche": date(2021, 2, 15),  # Plus de 24 mois -> 27 jours
                "departement": "Développement"
            },
            {
                "email": "marie.dupont@entreprise.com", 
                "password": "emp123",
                "nom": "Dupont",
                "prenom": "Marie",
                "telephone": "+33123456791",
                "numero_piece_identite": "DEV001",
                "poste": "Développeuse Full Stack Senior",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2024, 6, 1),  # Récent -> calcul prorata (~15 jours)
                "departement": "Développement"
            },
            {
                "email": "antoine.moreau@entreprise.com",
                "password": "emp123",
                "nom": "Moreau",
                "prenom": "Antoine",
                "telephone": "+33123456792",
                "numero_piece_identite": "DEV002",
                "poste": "Développeur Backend",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2023, 10, 1),  # 1 an au 10 janvier -> 27 jours
                "departement": "Développement"
            },
            {
                "email": "camille.roux@entreprise.com",
                "password": "emp123",
                "nom": "Roux",
                "prenom": "Camille",
                "telephone": "+33123456793",
                "numero_piece_identite": "DEV003",
                "poste": "Développeuse Frontend",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2022, 5, 20),  # Plus de 24 mois -> 27 jours
                "departement": "Développement"
            },
            {
                "email": "lucas.martin@entreprise.com",
                "password": "emp123",
                "nom": "Martin",
                "prenom": "Lucas",
                "telephone": "+33123456794",
                "numero_piece_identite": "DEV004",
                "poste": "Développeur DevOps",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2024, 1, 15),  # Moins d'1 an au 10 janvier -> prorata (~13 jours)
                "departement": "Développement"
            },
            
            # === DÉPARTEMENT MARKETING ===
            {
                "email": "chef.marketing@entreprise.com",
                "password": "chef123", 
                "nom": "Bernard",
                "prenom": "Sophie",
                "telephone": "+33123456795",
                "numero_piece_identite": "CHEF002",
                "poste": "Responsable Marketing",
                "role": RoleEnum.CHEF_SERVICE,
                "date_embauche": date(2020, 11, 10),  # Plus de 24 mois -> 27 jours
                "departement": "Marketing"
            },
            {
                "email": "julien.garcia@entreprise.com",
                "password": "emp123",
                "nom": "Garcia",
                "prenom": "Julien",
                "telephone": "+33123456796",
                "numero_piece_identite": "MKT001",
                "poste": "Responsable Communication",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2023, 3, 1),  # 1 an au 10 janvier -> 27 jours
                "departement": "Marketing"
            },
            {
                "email": "emma.leroy@entreprise.com",
                "password": "emp123",
                "nom": "Leroy",
                "prenom": "Emma",
                "telephone": "+33123456797",
                "numero_piece_identite": "MKT002",
                "poste": "Chargée de Marketing Digital",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2024, 9, 2),  # Très récent -> prorata (~7 jours)
                "departement": "Marketing"
            },
            {
                "email": "pierre.simon@entreprise.com",
                "password": "emp123",
                "nom": "Simon",
                "prenom": "Pierre",
                "telephone": "+33123456798",
                "numero_piece_identite": "MKT003",
                "poste": "Graphiste",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2022, 1, 10),  # Plus de 24 mois -> 27 jours
                "departement": "Marketing"
            },
            
            # === DÉPARTEMENT VENTES ===
            {
                "email": "chef.ventes@entreprise.com",
                "password": "chef123",
                "nom": "Rousseau",
                "prenom": "Nicolas",
                "telephone": "+33123456799",
                "numero_piece_identite": "CHEF003",
                "poste": "Directeur Commercial",
                "role": RoleEnum.CHEF_SERVICE,
                "date_embauche": date(2019, 6, 1),  # Plus de 24 mois -> 27 jours
                "departement": "Ventes"
            },
            {
                "email": "sarah.blanc@entreprise.com",
                "password": "emp123",
                "nom": "Blanc",
                "prenom": "Sarah",
                "telephone": "+33123456800",
                "numero_piece_identite": "VTE001",
                "poste": "Commerciale Senior",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2021, 8, 15),  # Plus de 24 mois -> 27 jours
                "departement": "Ventes"
            },
            {
                "email": "maxime.henry@entreprise.com",
                "password": "emp123",
                "nom": "Henry",
                "prenom": "Maxime",
                "telephone": "+33123456801",
                "numero_piece_identite": "VTE002",
                "poste": "Commercial",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2024, 3, 1),  # Moins d'1 an au 10 janvier -> prorata (~11 jours)
                "departement": "Ventes"
            },
            {
                "email": "celine.petit@entreprise.com",
                "password": "emp123",
                "nom": "Petit",
                "prenom": "Céline",
                "telephone": "+33123456802",
                "numero_piece_identite": "VTE003",
                "poste": "Assistante Commerciale",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2023, 7, 1),  # 1 an au 10 janvier -> 27 jours
                "departement": "Ventes"
            },
            {
                "email": "david.moreau@entreprise.com",
                "password": "emp123",
                "nom": "Moreau",
                "prenom": "David",
                "telephone": "+33123456803",
                "numero_piece_identite": "VTE004",
                "poste": "Commercial Junior",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2024, 11, 1),  # Très récent -> prorata (~2 jours)
                "departement": "Ventes"
            },
            
            # === DÉPARTEMENT RH (quelques employés) ===
            {
                "email": "amelie.durand@entreprise.com",
                "password": "emp123",
                "nom": "Durand",
                "prenom": "Amélie",
                "telephone": "+33123456804",
                "numero_piece_identite": "RH001",
                "poste": "Gestionnaire RH",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2022, 9, 1),  # Plus de 24 mois -> 27 jours
                "departement": "Direction des Ressources Humaines"
            },
            {
                "email": "kevin.martinez@entreprise.com",
                "password": "emp123",
                "nom": "Martinez",
                "prenom": "Kevin",
                "telephone": "+33123456805",
                "numero_piece_identite": "RH002",
                "poste": "Assistant RH",
                "role": RoleEnum.EMPLOYE,
                "date_embauche": date(2024, 4, 15),  # Moins d'1 an au 10 janvier -> prorata (~9 jours)
                "departement": "Direction des Ressources Humaines"
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