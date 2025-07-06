#!/usr/bin/env python3
"""
Script pour ajouter les champs d'annulation à la table demandes_conges
"""

import asyncio
from sqlalchemy import text
from models.database import get_database

async def add_annulation_fields():
    """Ajoute les nouveaux champs d'annulation à la table demandes_conges"""
    async for db in get_database():
        print("=== AJOUT DES CHAMPS D'ANNULATION ===")
        
        try:
            # Vérifier si les champs existent déjà
            result = await db.execute(text("PRAGMA table_info(demandes_conges)"))
            columns = [row[1] for row in result.fetchall()]
            
            print(f"Colonnes existantes: {columns}")
            
            # Ajouter les nouveaux champs un par un (SQLite ne supporte pas IF NOT EXISTS)
            if 'demande_annulation' not in columns:
                await db.execute(text("ALTER TABLE demandes_conges ADD COLUMN demande_annulation BOOLEAN DEFAULT FALSE"))
                print("✅ Champ 'demande_annulation' ajouté")
            else:
                print("ℹ️ Champ 'demande_annulation' déjà existant")
                
            if 'motif_annulation' not in columns:
                await db.execute(text("ALTER TABLE demandes_conges ADD COLUMN motif_annulation TEXT"))
                print("✅ Champ 'motif_annulation' ajouté")
            else:
                print("ℹ️ Champ 'motif_annulation' déjà existant")
                
            if 'date_demande_annulation' not in columns:
                await db.execute(text("ALTER TABLE demandes_conges ADD COLUMN date_demande_annulation TIMESTAMP"))
                print("✅ Champ 'date_demande_annulation' ajouté")
            else:
                print("ℹ️ Champ 'date_demande_annulation' déjà existant")
            
            await db.commit()
            print("✅ Migration terminée avec succès")
            
            # Vérifier les champs ajoutés
            result = await db.execute(text("PRAGMA table_info(demandes_conges)"))
            new_columns = result.fetchall()
            
            print("\n📋 Structure de la table après migration :")
            annulation_fields = []
            for col in new_columns:
                if col[1] in ['demande_annulation', 'motif_annulation', 'date_demande_annulation']:
                    annulation_fields.append(col)
                    print(f"  - {col[1]}: {col[2]} (nullable: {col[3] == 0}, default: {col[4]})")
                    
            if len(annulation_fields) == 3:
                print("✅ Tous les champs d'annulation sont présents")
            else:
                print(f"❌ Seulement {len(annulation_fields)}/3 champs d'annulation ajoutés")
                
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout des champs : {e}")
            await db.rollback()
            
        break

if __name__ == "__main__":
    asyncio.run(add_annulation_fields()) 