#!/usr/bin/env python3
"""
Script pour assigner un chef au département RH existant.
"""
import requests
import json
from uuid import UUID

# Configuration
API_BASE_URL = "http://localhost:8000/api"
DEPARTEMENT_RH_ID = "960c0a43-b058-4113-8458-1d70816d97fb"

def get_admin_token():
    """Récupère le token d'authentification pour l'admin."""
    login_url = f"{API_BASE_URL}/auth/login"
    login_data = {
        "username": "admin@admin.com",
        "password": "admin123"
    }
    
    response = requests.post(login_url, data=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Erreur lors de la connexion: {response.status_code}")
        print(response.text)
        return None

def get_drh_user(token):
    """Récupère l'utilisateur DRH."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Récupérer tous les utilisateurs
    users_url = f"{API_BASE_URL}/users"
    response = requests.get(users_url, headers=headers)
    
    if response.status_code == 200:
        users = response.json()
        # Chercher l'utilisateur DRH
        for user in users:
            if user.get("role") == "drh":
                return user
        print("Aucun utilisateur DRH trouvé")
        return None
    else:
        print(f"Erreur lors de la récupération des utilisateurs: {response.status_code}")
        print(response.text)
        return None

def assign_chef_to_departement(token, departement_id, chef_id):
    """Assigne un chef à un département."""
    headers = {"Authorization": f"Bearer {token}"}
    
    assign_url = f"{API_BASE_URL}/departements/{departement_id}/chef"
    params = {"chef_id": chef_id}
    
    response = requests.put(assign_url, headers=headers, params=params)
    
    if response.status_code == 200:
        print("Chef assigné avec succès!")
        return response.json()
    else:
        print(f"Erreur lors de l'assignation: {response.status_code}")
        print(response.text)
        return None

def main():
    print("=== Script d'assignation de chef au département RH ===")
    
    # Récupérer le token d'authentification
    print("Connexion en tant qu'admin...")
    token = get_admin_token()
    if not token:
        print("Impossible de se connecter")
        return
    
    # Récupérer l'utilisateur DRH
    print("Recherche de l'utilisateur DRH...")
    drh_user = get_drh_user(token)
    if not drh_user:
        print("Aucun utilisateur DRH trouvé")
        return
    
    print(f"Utilisateur DRH trouvé: {drh_user['nom']} {drh_user['prenom']} ({drh_user['email']})")
    
    # Assigner le DRH comme chef du département RH
    print("Assignation du DRH au département RH...")
    result = assign_chef_to_departement(token, DEPARTEMENT_RH_ID, drh_user['id'])
    
    if result:
        print(f"Département mis à jour: {result['nom']}")
        print(f"Chef assigné: {drh_user['nom']} {drh_user['prenom']}")
    else:
        print("Échec de l'assignation")

if __name__ == "__main__":
    main() 