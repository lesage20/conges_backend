#!/usr/bin/env python3
"""
Script de test pour vérifier le calcul automatique des jours de congés
"""

import asyncio
import sys
from pathlib import Path
from datetime import date

# Ajouter le répertoire parent (backend) au PYTHONPATH
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.database import async_session_maker
from models.user import User
from sqlalchemy import select

async def test_calcul_conges():
    """Teste le calcul automatique des jours de congés pour tous les utilisateurs"""
    
    async with async_session_maker() as session:
        # Récupérer tous les utilisateurs
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        print("🧮 Test du calcul automatique des jours de congés")
        print("=" * 60)
        
        for user in users:
            print(f"\n👤 {user.nom_complet}")
            print(f"   📧 Email: {user.email}")
            print(f"   📅 Date d'embauche: {user.date_embauche}")
            print(f"   🎯 Rôle: {user.role.value}")
            
            # Calculer l'ancienneté
            if user.date_embauche:
                today = date.today()
                anciennete_jours = (today - user.date_embauche).days
                anciennete_mois = anciennete_jours / 30.0
                anciennete_annees = anciennete_jours / 365.0
                
                print(f"   ⏱️  Ancienneté: {anciennete_jours} jours ({anciennete_mois:.1f} mois, {anciennete_annees:.1f} ans)")
                
                # Date du 10 janvier précédent
                annee_courante = today.year
                date_10_janvier_precedent = date(annee_courante - 1, 1, 10)
                print(f"   📍 Date 10 janvier précédent: {date_10_janvier_precedent}")
                print(f"   🔄 1 an au 10 janvier? {user.date_embauche <= date_10_janvier_precedent}")
                print(f"   🔄 Plus de 24 mois? {anciennete_mois >= 24}")
            
            # Calcul automatique des jours de congés
            jours_conges = user.solde_conges
            print(f"   🏖️  Jours de congés calculés: {jours_conges} jours")
            
            # Explication du calcul
            if user.date_embauche:
                if anciennete_mois >= 24:
                    print(f"   💡 Calcul: Plus de 24 mois → 12 * 2.2 = {12 * 2.2} → ceil = {jours_conges}")
                elif user.date_embauche <= date_10_janvier_precedent:
                    print(f"   💡 Calcul: 1 an au 10 janvier → 12 * 2.2 = {12 * 2.2} → ceil = {jours_conges}")
                else:
                    mois_travailles = anciennete_jours / 30.0
                    conges_bruts = mois_travailles * 2.2
                    print(f"   💡 Calcul: Prorata → {anciennete_jours} jours / 30 * 2.2 = {conges_bruts:.2f} → ceil = {jours_conges}")
            
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_calcul_conges()) 