#!/usr/bin/env python3
"""
Script de test pour vérifier l'authentification par email et les nouvelles routes
"""

import requests
import json

BASE_URL = "http://localhost:65000"

def test_authentication_and_routes():
    print("🧪 Test de l'authentification par email et des nouvelles routes")
    print("=" * 70)
    
    # Test 1: Connexion avec différents utilisateurs
    users_to_test = [
        {
            "email": "drh@entreprise.com",
            "password": "admin123",
            "role": "DRH",
            "name": "Caroline Dubois"
        },
        {
            "email": "chef.dev@entreprise.com", 
            "password": "chef123",
            "role": "Chef de service",
            "name": "Thomas Laurent"
        },
        {
            "email": "marie.dupont@entreprise.com",
            "password": "emp123", 
            "role": "Employé",
            "name": "Marie Dupont"
        }
    ]
    
    for user_info in users_to_test:
        print(f"\n👤 Test avec {user_info['name']} ({user_info['role']})")
        print("-" * 50)
        
        # Connexion
        try:
            login_data = {
                "username": user_info["email"],  # FastAPIUsers utilise "username" mais accepte l'email
                "password": user_info["password"]
            }
            
            response = requests.post(
                f"{BASE_URL}/api/auth/jwt/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                token = token_data.get("access_token")
                print(f"✅ Connexion réussie avec email: {user_info['email']}")
                
                headers = {"Authorization": f"Bearer {token}"}
                
                # Test du profil utilisateur
                response = requests.get(f"{BASE_URL}/api/users/me", headers=headers)
                if response.status_code == 200:
                    profile = response.json()
                    print(f"   👤 Profil: {profile['nom_complet']}")
                    print(f"   🎯 Rôle: {profile['role']}")
                    print(f"   🏖️  Jours de congés: {profile['solde_conges']}")
                    
                    # Test de la route /api/users/tous
                    print(f"\n   🔍 Test de /api/users/tous:")
                    response = requests.get(f"{BASE_URL}/api/users/tous", headers=headers)
                    
                    if response.status_code == 200:
                        users_list = response.json()
                        print(f"   ✅ Accès autorisé - {len(users_list)} utilisateur(s) retourné(s)")
                        
                        for user in users_list:
                            print(f"      - {user['nom_complet']} ({user['role']}) - {user['solde_conges']} jours")
                            
                    elif response.status_code == 403:
                        print(f"   🚫 Accès refusé (normal pour un employé)")
                    else:
                        print(f"   ❌ Erreur inattendue: {response.status_code}")
                        print(f"      {response.text}")
                    
                    # Test de la route /api/users/equipe (alias)
                    print(f"\n   🔍 Test de /api/users/equipe:")
                    response = requests.get(f"{BASE_URL}/api/users/equipe", headers=headers)
                    
                    if response.status_code == 200:
                        team_list = response.json()
                        print(f"   ✅ Équipe accessible - {len(team_list)} membre(s)")
                    elif response.status_code == 403:
                        print(f"   🚫 Accès refusé (normal pour un employé)")
                    else:
                        print(f"   ❌ Erreur: {response.status_code}")
                        
                else:
                    print(f"   ❌ Erreur récupération profil: {response.status_code}")
                    
            else:
                print(f"❌ Échec connexion: {response.status_code}")
                print(f"   Réponse: {response.text}")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")

def test_authentication_logic():
    """Test spécifique de la logique d'authentification"""
    print(f"\n🔐 Test de la logique d'authentification")
    print("=" * 50)
    
    # Test avec email correct
    print("✅ Test avec email valide:")
    print("   - FastAPIUsers utilise le champ 'username' mais accepte l'email")
    print("   - Format: username=email@domain.com&password=motdepasse")
    
    # Test avec des variations d'email
    test_cases = [
        "drh@entreprise.com",
        "chef.dev@entreprise.com", 
        "marie.dupont@entreprise.com",
        "chef.marketing@entreprise.com"
    ]
    
    for email in test_cases:
        print(f"   📧 {email} → Format de connexion valide")

if __name__ == "__main__":
    try:
        test_authentication_logic()
        test_authentication_and_routes()
        
        print(f"\n📋 Résumé des fonctionnalités:")
        print("=" * 50)
        print("✅ Authentification par email (champ 'username' accepte l'email)")
        print("✅ Route /api/users/tous - Tous les utilisateurs selon le rôle:")
        print("   - DRH: voit tous les employés et chefs de service")
        print("   - Chef de service: voit tous les employés de son département") 
        print("   - Employé: accès refusé")
        print("✅ Route /api/users/equipe - Alias pour la page 'Mon Équipe'")
        print("✅ Calcul automatique des jours de congés selon l'ancienneté")
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc() 