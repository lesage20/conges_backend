#!/usr/bin/env python3
"""
Script pour corriger le format des UUIDs dans la base de données
Convertir tous les UUIDs en format avec tirets (format standard)
"""

import sqlite3
import uuid

def fix_uuid_formats():
    """Corrige les formats UUID pour qu'ils soient cohérents"""
    
    conn = sqlite3.connect('conges.db')
    cursor = conn.cursor()
    
    try:
        print("=== Correction des formats UUID ===")
        
        # 1. Corriger demandes_conges.demandeur_id
        print("1. Correction demandes_conges.demandeur_id...")
        cursor.execute("SELECT id, demandeur_id FROM demandes_conges")
        demandes = cursor.fetchall()
        
        for demande_id, demandeur_id in demandes:
            if demandeur_id and len(demandeur_id) == 32:  # Format sans tirets
                # Convertir en format avec tirets
                uuid_obj = uuid.UUID(demandeur_id)
                formatted_uuid = str(uuid_obj)
                
                cursor.execute(
                    "UPDATE demandes_conges SET demandeur_id = ? WHERE id = ?",
                    (formatted_uuid, demande_id)
                )
                print(f"  Corrigé: {demandeur_id} -> {formatted_uuid}")
        
        # 2. Corriger demandes_conges.valideur_id si nécessaire
        print("2. Correction demandes_conges.valideur_id...")
        cursor.execute("SELECT id, valideur_id FROM demandes_conges WHERE valideur_id IS NOT NULL")
        demandes_valideur = cursor.fetchall()
        
        for demande_id, valideur_id in demandes_valideur:
            if valideur_id and len(valideur_id) == 32:  # Format sans tirets
                # Convertir en format avec tirets
                uuid_obj = uuid.UUID(valideur_id)
                formatted_uuid = str(uuid_obj)
                
                cursor.execute(
                    "UPDATE demandes_conges SET valideur_id = ? WHERE id = ?",
                    (formatted_uuid, demande_id)
                )
                print(f"  Corrigé valideur: {valideur_id} -> {formatted_uuid}")
        
        # 3. Corriger users.departement_id si nécessaire
        print("3. Correction users.departement_id...")
        cursor.execute("SELECT id, departement_id FROM users WHERE departement_id IS NOT NULL")
        users_dept = cursor.fetchall()
        
        for user_id, dept_id in users_dept:
            if dept_id and len(dept_id) == 32:  # Format sans tirets
                # Convertir en format avec tirets
                uuid_obj = uuid.UUID(dept_id)
                formatted_uuid = str(uuid_obj)
                
                cursor.execute(
                    "UPDATE users SET departement_id = ? WHERE id = ?",
                    (formatted_uuid, user_id)
                )
                print(f"  Corrigé dept: {dept_id} -> {formatted_uuid}")
        
        # 4. Vérifier que tout est maintenant correct
        print("4. Vérification finale...")
        cursor.execute("""
            SELECT d.id, d.demandeur_id, u.id, u.nom, u.prenom 
            FROM demandes_conges d 
            LEFT JOIN users u ON d.demandeur_id = u.id 
            LIMIT 3
        """)
        
        results = cursor.fetchall()
        for row in results:
            if row[2]:  # Si user_id n'est pas None
                print(f"✅ JOIN réussi: demande={row[0]}, user={row[3]} {row[4]}")
            else:
                print(f"❌ JOIN toujours échoué: demande={row[0]}, demandeur_id={row[1]}")
        
        # Valider les changements
        conn.commit()
        print("✅ Tous les changements ont été validés!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()
        print("Connexion fermée.")

if __name__ == "__main__":
    fix_uuid_formats() 