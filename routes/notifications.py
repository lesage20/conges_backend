#!/usr/bin/env python3
"""
Routes API pour la gestion des notifications
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_database
from models.notification import NotificationRead, NotificationUpdate
from models.user import User
from utils.dependencies import get_current_user
from services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/", response_model=List[NotificationRead])
async def get_my_notifications(
    non_lues_seulement: bool = Query(False, description="Ne récupérer que les notifications non lues"),
    limit: int = Query(50, le=100, description="Nombre maximum de notifications à récupérer"),
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère les notifications de l'utilisateur connecté"""
    service = NotificationService(db)
    notifications = await service.get_notifications_utilisateur(
        user_id=current_user.id,
        non_lues_seulement=non_lues_seulement,
        limit=limit
    )
    
    return [NotificationRead.from_orm(notif) for notif in notifications]

@router.get("/count")
async def get_notifications_count(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Récupère le nombre de notifications non lues"""
    service = NotificationService(db)
    notifications_non_lues = await service.get_notifications_utilisateur(
        user_id=current_user.id,
        non_lues_seulement=True
    )
    
    return {
        "total_non_lues": len(notifications_non_lues)
    }

@router.put("/{notification_id}/marquer-lue")
async def marquer_notification_lue(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Marque une notification comme lue"""
    service = NotificationService(db)
    success = await service.marquer_comme_lue(notification_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    return {"message": "Notification marquée comme lue"}

@router.put("/marquer-toutes-lues")
async def marquer_toutes_notifications_lues(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """Marque toutes les notifications de l'utilisateur comme lues"""
    service = NotificationService(db)
    notifications_non_lues = await service.get_notifications_utilisateur(
        user_id=current_user.id,
        non_lues_seulement=True
    )
    
    for notification in notifications_non_lues:
        await service.marquer_comme_lue(notification.id, current_user.id)
    
    return {
        "message": f"{len(notifications_non_lues)} notifications marquées comme lues"
    } 