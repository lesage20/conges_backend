#!/usr/bin/env python3
"""
Script pour corriger les URLs d'attestation manquantes
"""

import asyncio
from sqlalchemy import select, text
from models.database import engine
from models.demande_conge import DemandeConge

async def fix_attestation_urls():
    """Met à jour les URLs d'attestation manquantes"""
    async with engine.begin() as conn:
        # Vérifier les demandes avec attestation_pdf mais sans attestation_url
        result = await conn.execute(text("""
            SELECT id, attestation_pdf, attestation_url 
            FROM demandes_conges 
            WHERE attestation_pdf IS NOT NULL
        """))
        
        rows = result.fetchall()
        print(f"Trouvé {len(rows)} demandes avec attestations:")
        
        for row in rows:
            demande_id, pdf_filename, current_url = row
            print(f"  ID: {demande_id}, PDF: {pdf_filename}, URL actuelle: {current_url}")
            
            # Si l'URL est manquante, la générer
            if not current_url and pdf_filename:
                new_url = f"http://localhost:8000/attestations/{pdf_filename}"
                await conn.execute(text("""
                    UPDATE demandes_conges 
                    SET attestation_url = :url 
                    WHERE id = :id
                """), {"url": new_url, "id": demande_id})
                print(f"    ✓ URL mise à jour: {new_url}")
        
        print("✓ Correction terminée")

if __name__ == "__main__":
    print("Correction des URLs d'attestation...")
    asyncio.run(fix_attestation_urls()) 