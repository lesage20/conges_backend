#!/usr/bin/env python3
"""
Script de migration pour ajouter le champ attestation_url à la table demandes_conges
"""

import asyncio
from sqlalchemy import text
from models.database import engine

async def add_attestation_url_field():
    """Ajoute le champ attestation_url à la table demandes_conges"""
    async with engine.begin() as conn:
        # Vérifier si la colonne existe déjà (SQLite)
        result = await conn.execute(text("""
            PRAGMA table_info(demandes_conges)
        """))
        
        existing_columns = [row[1] for row in result]  # row[1] contient le nom de la colonne
        
        # Ajouter attestation_url si elle n'existe pas
        if 'attestation_url' not in existing_columns:
            await conn.execute(text("""
                ALTER TABLE demandes_conges 
                ADD COLUMN attestation_url VARCHAR NULL
            """))
            print("✓ Colonne attestation_url ajoutée")
        else:
            print("✓ Colonne attestation_url existe déjà")

        # Mettre à jour les URL existantes pour les attestations qui ont déjà un fichier
        await conn.execute(text("""
            UPDATE demandes_conges 
            SET attestation_url = 'http://localhost:8000/attestations/' || attestation_pdf
            WHERE attestation_pdf IS NOT NULL AND attestation_url IS NULL
        """))
        print("✓ URLs d'attestation mises à jour pour les fichiers existants")

if __name__ == "__main__":
    print("Migration: Ajout du champ attestation_url")
    asyncio.run(add_attestation_url_field())
    print("✓ Migration terminée") 