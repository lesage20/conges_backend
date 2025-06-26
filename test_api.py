#!/usr/bin/env python3
"""
Script de test simple pour vérifier que l'API fonctionne
"""

import requests
import json

BASE_URL = "http://localhost:65000"

def test_api():
    print("🧪 Test de l'API FastAPI...")
    
    # Test 1: Vérifier que l'API répond
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ API accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur connexion API: {e}")
        return
    
    # Test 2: Tentative de connexion avec l'admin
    try:
        login_data = {
            "username": "admin@company.com",
            "password": "admin123"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/auth/jwt/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            print(f"✅ Connexion réussie! Token reçu.")
            
            # Test 3: Vérifier l'accès avec le token
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(f"{BASE_URL}/api/users/me", headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Profil utilisateur récupéré: {user_data['email']}")
                print(f"   Nom: {user_data['prenom']} {user_data['nom']}")
                print(f"   Rôle: {user_data['role']}")
            else:
                print(f"❌ Erreur récupération profil: {response.status_code}")
                
        else:
            print(f"❌ Erreur connexion: {response.status_code}")
            print(f"   Réponse: {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur test authentification: {e}")

if __name__ == "__main__":
    test_api() 