#!/usr/bin/env python3
"""
Script pour tester l'API et voir le problème avec les données utilisateur
"""
import requests
import json

def test_api():
    """Test l'API pour voir si les informations utilisateur sont correctement retournées"""
    
    # Configuration de base
    BASE_URL = "http://localhost:8000/api"
    
    # Test 1: Récupérer les demandes sans authentification (devrait échouer)
    print("=== Test 1: Récupération des demandes sans authentification ===")
    try:
        response = requests.get(f"{BASE_URL}/demandes-conges/mes-demandes")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("✅ Authentification requise comme attendu")
        else:
            print("❌ Authentification non requise - problème de sécurité")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Vérifier la structure des données avec un token test
    print("=== Test 2: Test avec token (probablement expiré) ===")
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyMDRkOThkOC1lN2I1LTRkZDUtOGIwOC02YzAwM2NmYzEzNzIiLCJhdWQiOlsiZmFzdGFwaS11c2VyczphdXRoIl0sImV4cCI6MTc1MTc3MjcwN30.T5q6JwMik51-OUCIwSuyxlp80xmCBgPJW4QPUunYr48"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/demandes-conges/mes-demandes", headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Données reçues: {json.dumps(data, indent=2, default=str)}")
        else:
            print(f"Erreur: {response.text}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Vérifier les endpoints disponibles
    print("=== Test 3: Vérification des endpoints ===")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"Documentation API accessible: {response.status_code == 200}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Tester la base de données directement
    print("=== Test 4: Test direct de la base de données ===")
    try:
        from models.database import get_database
        from models.demande_conge import DemandeConge
        from models.user import User
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        import asyncio
        
        async def test_db():
            async for db in get_database():
                # Récupérer une demande avec les relations
                result = await db.execute(
                    select(DemandeConge)
                    .options(selectinload(DemandeConge.demandeur))
                    .limit(1)
                )
                demande = result.scalar_one_or_none()
                
                if demande:
                    print(f"Demande trouvée: {demande.id}")
                    print(f"Demandeur ID: {demande.demandeur_id}")
                    print(f"Working time: {demande.working_time}")
                    print(f"Real time: {demande.real_time}")
                    print(f"Demandeur object: {demande.demandeur}")
                    
                    if demande.demandeur:
                        print(f"Demandeur nom: {demande.demandeur.nom}")
                        print(f"Demandeur email: {demande.demandeur.email}")
                    else:
                        print("❌ Demandeur est None - problème de relation")
                        
                        # Test manuel : récupérer l'utilisateur séparément
                        user_result = await db.execute(
                            select(User).where(User.id == demande.demandeur_id)
                        )
                        user = user_result.scalar_one_or_none()
                        if user:
                            print(f"Utilisateur existe: {user.nom} {user.prenom}")
                        else:
                            print("❌ Utilisateur n'existe pas!")
                else:
                    print("❌ Aucune demande trouvée")
                break
        
        asyncio.run(test_db())
        
    except Exception as e:
        print(f"❌ Erreur base de données: {e}")

if __name__ == "__main__":
    test_api() 