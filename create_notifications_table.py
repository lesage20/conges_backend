#!/usr/bin/env python3
"""
Script pour créer la table notifications dans la base de données
"""

import asyncio
from sqlalchemy import text
from models.database import get_database

async def create_notifications_table():
    """Crée la table notifications si elle n'existe pas"""
    async for db in get_database():
        print("=== CRÉATION DE LA TABLE NOTIFICATIONS ===")
        
        try:
            # Vérifier si la table existe déjà
            result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'"))
            table_exists = result.fetchone() is not None
            
            if table_exists:
                print("ℹ️ La table 'notifications' existe déjà")
                return
            
            # Créer la table notifications
            create_table_sql = """
            CREATE TABLE notifications (
                id TEXT PRIMARY KEY,
                destinataire_id TEXT NOT NULL,
                type_notification TEXT NOT NULL,
                titre TEXT NOT NULL,
                message TEXT NOT NULL,
                demande_conge_id TEXT,
                lue BOOLEAN DEFAULT FALSE,
                email_envoye BOOLEAN DEFAULT FALSE,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_lecture TIMESTAMP,
                date_envoi_email TIMESTAMP,
                FOREIGN KEY (destinataire_id) REFERENCES users (id),
                FOREIGN KEY (demande_conge_id) REFERENCES demandes_conges (id)
            )
            """
            
            await db.execute(text(create_table_sql))
            await db.commit()
            print("✅ Table 'notifications' créée avec succès")
            
            # Créer des index pour améliorer les performances
            index_sql = [
                "CREATE INDEX idx_notifications_destinataire ON notifications(destinataire_id)",
                "CREATE INDEX idx_notifications_lue ON notifications(lue)",
                "CREATE INDEX idx_notifications_date_creation ON notifications(date_creation DESC)",
                "CREATE INDEX idx_notifications_demande_conge ON notifications(demande_conge_id)"
            ]
            
            for idx_sql in index_sql:
                await db.execute(text(idx_sql))
            
            await db.commit()
            print("✅ Index créés avec succès")
            
        except Exception as e:
            print(f"❌ Erreur lors de la création de la table : {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(create_notifications_table()) 