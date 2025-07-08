#!/usr/bin/env python3
"""
Script pour envoyer les rappels automatiques de congés
À exécuter quotidiennement (par exemple via cron ou tâche planifiée)
"""

import asyncio
from datetime import datetime

from models.database import get_database
from services.notification_service import NotificationService

async def executer_rappels_automatiques():
    """Exécute les rappels automatiques quotidiens"""
    print(f"=== EXÉCUTION DES RAPPELS AUTOMATIQUES - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ===")
    
    async for db in get_database():
        try:
            service = NotificationService(db)
            notifications = await service.generer_rappels_automatiques()
            
            print(f"✅ {len(notifications)} rappels automatiques envoyés")
            
            # Log des notifications envoyées
            for notification in notifications:
                print(f"   - {notification.type_notification.value}: {notification.titre}")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution des rappels automatiques: {e}")
        
        # On ne traite qu'une seule session DB
        break
    
    print("=== FIN DES RAPPELS AUTOMATIQUES ===")

if __name__ == "__main__":
    asyncio.run(executer_rappels_automatiques()) 