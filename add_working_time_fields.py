#!/usr/bin/env python3
"""
Script pour ajouter les champs working_time et real_time à la table demandes_conges
et mettre à jour les données existantes
"""

import asyncio
import sqlite3
from datetime import datetime
from utils.date_calculator import calculate_days_details

async def add_working_time_fields():
    """Ajoute les nouveaux champs et met à jour les données existantes"""
    
    # Connexion à la base de données SQLite
    conn = sqlite3.connect('conges.db')
    cursor = conn.cursor()
    
    try:
        # Ajouter les nouvelles colonnes
        print("Ajout des nouvelles colonnes...")
        
        cursor.execute("""
            ALTER TABLE demandes_conges 
            ADD COLUMN working_time INTEGER;
        """)
        
        cursor.execute("""
            ALTER TABLE demandes_conges 
            ADD COLUMN real_time INTEGER;
        """)
        
        print("Colonnes ajoutées avec succès!")
        
        # Récupérer toutes les demandes existantes
        cursor.execute("""
            SELECT id, date_debut, date_fin, nombre_jours
            FROM demandes_conges
        """)
        
        demandes = cursor.fetchall()
        print(f"Mise à jour de {len(demandes)} demandes existantes...")
        
        # Mettre à jour chaque demande
        for demande_id, date_debut, date_fin, nombre_jours in demandes:
            try:
                # Convertir les dates string en objets date
                date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
                date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
                
                # Calculer les nouveaux champs
                working_days, total_days, formatted_string = calculate_days_details(
                    date_debut_obj, date_fin_obj
                )
                
                # Mettre à jour la demande
                cursor.execute("""
                    UPDATE demandes_conges 
                    SET working_time = ?, real_time = ?, nombre_jours = ?
                    WHERE id = ?
                """, (working_days, total_days, formatted_string, demande_id))
                
                print(f"  Demande {demande_id}: {working_days} jours ouvrables, {total_days} jours total")
                
            except Exception as e:
                print(f"  Erreur pour la demande {demande_id}: {e}")
                continue
        
        # Valider les changements
        conn.commit()
        print("Toutes les demandes ont été mises à jour avec succès!")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Les colonnes existent déjà. Mise à jour des données existantes...")
            
            # Récupérer toutes les demandes existantes
            cursor.execute("""
                SELECT id, date_debut, date_fin
                FROM demandes_conges
                WHERE working_time IS NULL OR real_time IS NULL
            """)
            
            demandes = cursor.fetchall()
            print(f"Mise à jour de {len(demandes)} demandes avec des valeurs manquantes...")
            
            # Mettre à jour chaque demande
            for demande_id, date_debut, date_fin in demandes:
                try:
                    # Convertir les dates string en objets date
                    date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
                    date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
                    
                    # Calculer les nouveaux champs
                    working_days, total_days, formatted_string = calculate_days_details(
                        date_debut_obj, date_fin_obj
                    )
                    
                    # Mettre à jour la demande
                    cursor.execute("""
                        UPDATE demandes_conges 
                        SET working_time = ?, real_time = ?, nombre_jours = ?
                        WHERE id = ?
                    """, (working_days, total_days, formatted_string, demande_id))
                    
                    print(f"  Demande {demande_id}: {working_days} jours ouvrables, {total_days} jours total")
                    
                except Exception as e:
                    print(f"  Erreur pour la demande {demande_id}: {e}")
                    continue
            
            # Valider les changements
            conn.commit()
            print("Données mises à jour avec succès!")
        else:
            print(f"Erreur lors de l'ajout des colonnes: {e}")
            raise
    
    finally:
        conn.close()
        print("Connexion à la base de données fermée.")

if __name__ == "__main__":
    asyncio.run(add_working_time_fields()) 