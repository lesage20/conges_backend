"""
Script simple pour créer le département RH et configurer la hiérarchie
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api"

def get_token():
    """Obtenir un token d'authentification avec le DRH"""
    # Vous devez avoir un DRH existant dans votre base
    # Utilisez ses identifiants pour obtenir un token
    login_data = {
        "username": "caroline.dubois@test.com",  # Email du DRH
        "password": "password123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"]
    else:
        print(f"Erreur lors de la connexion: {response.status_code}")
        print(response.text)
        return None

def create_rh_department(token):
    """Créer le département Ressources Humaines"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Vérifier si le département existe déjà
    response = requests.get(f"{BASE_URL}/departements/", headers=headers)
    if response.status_code == 200:
        departements = response.json()
        for dept in departements:
            if dept["nom"] in ["Ressources Humaines", "RH", "DRH"]:
                print(f"✅ Département RH déjà existant: {dept['nom']} (ID: {dept['id']})")
                return dept["id"]
    
    # Créer le département
    dept_data = {
        "nom": "Ressources Humaines",
        "description": "Département de gestion des ressources humaines",
        "budget_conges": "0"
    }
    
    response = requests.post(f"{BASE_URL}/departements/", 
                           headers=headers, 
                           json=dept_data)
    
    if response.status_code == 200:
        dept = response.json()
        print(f"✅ Département RH créé: {dept['nom']} (ID: {dept['id']})")
        return dept["id"]
    else:
        print(f"❌ Erreur lors de la création du département: {response.status_code}")
        print(response.text)
        return None

def get_drh_user(token):
    """Récupérer l'utilisateur DRH"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Récupérer l'utilisateur actuel (le DRH connecté)
    response = requests.get(f"{BASE_URL}/users/me", headers=headers)
    if response.status_code == 200:
        user = response.json()
        if user["role"] == "drh":
            print(f"✅ DRH trouvé: {user['prenom']} {user['nom']} (ID: {user['id']})")
            return user
        else:
            print(f"❌ L'utilisateur connecté n'est pas DRH: {user['role']}")
            return None
    else:
        print(f"❌ Erreur lors de la récupération de l'utilisateur: {response.status_code}")
        return None

def assign_drh_to_department(token, dept_id, drh_id):
    """Assigner le DRH au département et comme chef"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Assigner le DRH au département
    response = requests.put(f"{BASE_URL}/users/{drh_id}/departement?departement_id={dept_id}",
                           headers=headers)
    
    if response.status_code == 200:
        print("✅ DRH assigné au département Ressources Humaines")
    else:
        print(f"❌ Erreur lors de l'assignation du DRH au département: {response.status_code}")
        print(response.text)
    
    # Assigner le DRH comme chef du département
    response = requests.put(f"{BASE_URL}/departements/{dept_id}/chef?chef_id={drh_id}",
                           headers=headers)
    
    if response.status_code == 200:
        print("✅ DRH défini comme chef du département Ressources Humaines")
    else:
        print(f"❌ Erreur lors de l'assignation comme chef: {response.status_code}")
        print(response.text)

def main():
    print("🔧 Configuration du département Ressources Humaines via API...")
    
    # 1. Obtenir le token
    token = get_token()
    if not token:
        print("❌ Impossible d'obtenir un token d'authentification")
        return
    
    # 2. Récupérer l'utilisateur DRH
    drh = get_drh_user(token)
    if not drh:
        return
    
    # 3. Créer ou récupérer le département RH
    dept_id = create_rh_department(token)
    if not dept_id:
        return
    
    # 4. Assigner le DRH au département
    assign_drh_to_department(token, dept_id, drh["id"])
    
    print("\n🎉 Configuration terminée avec succès !")
    print("📋 Résumé de la hiérarchie:")
    print(f"   • DRH: {drh['prenom']} {drh['nom']}")
    print(f"   • Chef du département RH: {drh['prenom']} {drh['nom']}")
    print(f"   • Règles d'approbation:")
    print(f"     - Demandes DRH: Auto-approuvées")
    print(f"     - Demandes chefs de service: Validées par le DRH")
    print(f"     - Demandes employés RH: Validées par le DRH")
    print(f"     - Demandes employés autres départements: Validées par leur chef de service")

if __name__ == "__main__":
    main() 