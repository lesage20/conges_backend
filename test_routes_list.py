#!/usr/bin/env python3
"""
Script pour lister toutes les routes disponibles de l'application
"""

import requests
import json

BASE_URL = "http://localhost:65000"

def test_routes():
    print("🔍 Test des routes disponibles")
    print("=" * 50)
    
    # Test des routes de base
    routes_to_test = [
        "/",
        "/health",
        "/docs",
        "/api/auth/jwt/login",
        "/api/users/me",
        "/api/users/tous",
        "/api/users/equipe",
        "/api/departements",
        "/api/demandes-conges"
    ]
    
    for route in routes_to_test:
        try:
            response = requests.get(f"{BASE_URL}{route}")
            print(f"✅ {route} → {response.status_code}")
            if response.status_code == 404:
                print(f"   ❌ Route non trouvée")
            elif response.status_code == 401:
                print(f"   🔐 Authentification requise")
            elif response.status_code == 200:
                print(f"   ✅ OK")
        except Exception as e:
            print(f"❌ {route} → Erreur: {e}")
    
    # Test spécifique pour les routes avec authentification
    print(f"\n🔐 Test avec authentification")
    print("-" * 30)
    
    # D'abord se connecter pour obtenir un token
    login_data = {
        "username": "drh@entreprise.com",
        "password": "admin123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/jwt/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            print(f"✅ Connexion réussie")
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test des routes protégées
            protected_routes = [
                "/api/users/me",
                "/api/users/tous", 
                "/api/users/equipe"
            ]
            
            for route in protected_routes:
                try:
                    response = requests.get(f"{BASE_URL}{route}", headers=headers)
                    print(f"✅ {route} → {response.status_code}")
                    if response.status_code == 404:
                        print(f"   ❌ Route non trouvée")
                    elif response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            print(f"   📊 Retourne {len(data)} éléments")
                        else:
                            print(f"   📊 Retourne un objet")
                except Exception as e:
                    print(f"❌ {route} → Erreur: {e}")
        else:
            print(f"❌ Échec connexion: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"❌ Erreur authentification: {e}")

if __name__ == "__main__":
    test_routes() 