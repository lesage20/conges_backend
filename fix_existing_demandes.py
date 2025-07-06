#!/usr/bin/env python3
"""
Script pour corriger les demandes existantes sans valideur assigné
"""

import asyncio
from models.database import get_database
from models.demande_conge import DemandeConge
from models.user import User, RoleEnum
from sqlalchemy import select, and_, update

async def fix_existing_demandes():
    """Corrige les demandes existantes sans valideur assigné"""
    async for db in get_database():
        print("=== CORRECTION DES DEMANDES EXISTANTES ===")
        
        # 1. Récupérer toutes les demandes sans valideur
        result = await db.execute(
            select(DemandeConge).where(DemandeConge.valideur_id.is_(None))
        )
        demandes_sans_valideur = result.scalars().all()
        
        print(f"Nombre de demandes sans valideur: {len(demandes_sans_valideur)}")
        
        if len(demandes_sans_valideur) == 0:
            print("✅ Aucune demande à corriger")
            break
            
        # 2. Corriger chaque demande
        corrections = 0
        for demande in demandes_sans_valideur:
            print(f"\n--- Correction demande {demande.id} ---")
            
            # Récupérer l'utilisateur demandeur
            user_result = await db.execute(
                select(User).where(User.id == demande.demandeur_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                print(f"❌ Utilisateur demandeur non trouvé: {demande.demandeur_id}")
                continue
                
            print(f"Demandeur: {user.nom} {user.prenom} ({user.role.value})")
            
            # Appliquer la logique d'assignation automatique
            valideur_id = None
            
            if user.role == RoleEnum.CHEF_SERVICE:
                # Chef de service → DRH
                drh_result = await db.execute(
                    select(User).where(User.role == RoleEnum.DRH).limit(1)
                )
                drh = drh_result.scalar_one_or_none()
                if drh:
                    valideur_id = drh.id
                    print(f"✅ Chef de service → DRH assigné: {drh.nom} {drh.prenom}")
                else:
                    print("❌ Aucun DRH trouvé")
                    
            elif user.role == RoleEnum.EMPLOYE and user.departement_id:
                # Employé → Chef de service de son département
                chef_result = await db.execute(
                    select(User).where(
                        and_(
                            User.departement_id == user.departement_id,
                            User.role == RoleEnum.CHEF_SERVICE
                        )
                    )
                )
                chef = chef_result.scalar_one_or_none()
                
                if chef:
                    valideur_id = chef.id
                    print(f"✅ Employé → Chef de service assigné: {chef.nom} {chef.prenom}")
                else:
                    # Pas de chef de service → DRH
                    drh_result = await db.execute(
                        select(User).where(User.role == RoleEnum.DRH).limit(1)
                    )
                    drh = drh_result.scalar_one_or_none()
                    if drh:
                        valideur_id = drh.id
                        print(f"✅ Pas de chef de service → DRH assigné: {drh.nom} {drh.prenom}")
                    else:
                        print("❌ Aucun DRH trouvé")
            else:
                print("❌ Utilisateur DRH ou sans département, pas de valideur automatique")
                
            # Mettre à jour la demande si on a trouvé un valideur
            if valideur_id:
                await db.execute(
                    update(DemandeConge)
                    .where(DemandeConge.id == demande.id)
                    .values(valideur_id=valideur_id)
                )
                corrections += 1
                print(f"✅ Demande mise à jour avec valideur: {valideur_id}")
            else:
                print("❌ Aucun valideur trouvé pour cette demande")
                
        # 3. Sauvegarder les modifications
        await db.commit()
        print(f"\n✅ {corrections} demandes corrigées avec succès")
        
        # 4. Vérification finale
        result = await db.execute(
            select(DemandeConge).where(DemandeConge.valideur_id.is_(None))
        )
        demandes_restantes = result.scalars().all()
        print(f"Demandes restantes sans valideur: {len(demandes_restantes)}")
        
        break

if __name__ == "__main__":
    asyncio.run(fix_existing_demandes()) 