#!/usr/bin/env python3
"""
Script de migration pour ajouter les champs attestation_pdf et date_generation_attestation
à la table demandes_conges.
"""

import asyncio
from sqlalchemy import text
from models.database import get_database

async def add_attestation_fields():
    """Ajoute les champs attestation_pdf et date_generation_attestation à la table demandes_conges"""
    async for db in get_database():
        try:
            # Vérifier si les colonnes existent déjà (SQLite)
            result = await db.execute(text("""
                PRAGMA table_info(demandes_conges)
            """))
            existing_columns = [row[1] for row in result.fetchall()]
            
            # Ajouter attestation_pdf si elle n'existe pas
            if 'attestation_pdf' not in existing_columns:
                await db.execute(text("""
                    ALTER TABLE demandes_conges 
                    ADD COLUMN attestation_pdf VARCHAR NULL
                """))
                print("✓ Colonne attestation_pdf ajoutée")
            else:
                print("✓ Colonne attestation_pdf existe déjà")
            
            # Ajouter date_generation_attestation si elle n'existe pas
            if 'date_generation_attestation' not in existing_columns:
                await db.execute(text("""
                    ALTER TABLE demandes_conges 
                    ADD COLUMN date_generation_attestation TIMESTAMP NULL
                """))
                print("✓ Colonne date_generation_attestation ajoutée")
            else:
                print("✓ Colonne date_generation_attestation existe déjà")
            
            await db.commit()
            print("\n✅ Migration terminée avec succès")
            
        except Exception as e:
            print(f"❌ Erreur lors de la migration : {e}")
            await db.rollback()
            raise
        finally:
            await db.close()
            break

if __name__ == "__main__":
    asyncio.run(add_attestation_fields()) 