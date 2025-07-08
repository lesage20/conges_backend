from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
import uuid

from models.user import UserRead, UserCreate, User
from utils.auth import auth_backend, fastapi_users, get_user_manager
from utils.dependencies import get_user_db

router = APIRouter()

# Modèle pour la réponse de login
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead

# Modèle pour changer le mot de passe
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# Modèle pour la réponse de changement de mot de passe
class ChangePasswordResponse(BaseModel):
    message: str

# Route de login personnalisée
@router.post("/auth/login", response_model=LoginResponse, tags=["auth"])
async def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_manager=Depends(get_user_manager)
):
    """
    Route de connexion personnalisée qui retourne le token et les informations utilisateur
    """
    try:
        # Vérifier l'utilisateur par email
        user = await user_manager.get_by_email(credentials.username)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Vérifier le mot de passe
        is_valid = user_manager.password_helper.verify_and_update(
            credentials.password, user.hashed_password
        )[0]
        
        if not is_valid or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Générer le token
        strategy = auth_backend.get_strategy()
        token = await strategy.write_token(user)
        
        # Calculer le solde de congés restant de manière asynchrone
        from models.demande_conge import DemandeConge
        from models.database import get_database
        from sqlalchemy import select
        
        # Récupérer les demandes de l'utilisateur de manière asynchrone
        async for db in get_database():
            demandes_result = await db.execute(
                select(DemandeConge).where(DemandeConge.demandeur_id == user.id)
            )
            demandes = demandes_result.scalars().all()
            break
        
        # Calculer le solde restant avec la méthode safe
        solde_restant = user.calculate_solde_conges_restant(demandes)
        
        # Créer la réponse utilisateur avec tous les champs calculés
        user_response = UserRead(
            id=user.id,
            email=user.email,
            nom=user.nom,
            prenom=user.prenom,
            nom_complet=user.nom_complet,
            telephone=user.telephone,
            numero_piece_identite=user.numero_piece_identite,
            poste=user.poste,
            role=user.role,
            date_embauche=user.date_embauche,
            solde_conges=user.solde_conges,
            solde_conges_restant=solde_restant,
            departement_id=user.departement_id,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_verified=user.is_verified,
            date_naissance=user.date_naissance,
            nombre_enfants=user.nombre_enfants,
            has_medaille_honneur=user.has_medaille_honneur,
            genre=user.genre
        )
        
        # Retourner le token avec les informations utilisateur
        return LoginResponse(
            access_token=token,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erreur d'authentification: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur d'authentification",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Route pour récupérer les infos de l'utilisateur connecté
@router.get("/users/me", response_model=UserRead, tags=["users"])
async def get_current_user_info(
    current_user: User = Depends(fastapi_users.current_user(active=True))
):
    """
    Récupère les informations de l'utilisateur actuellement connecté
    """
    # Calculer le solde de congés restant de manière asynchrone
    from models.demande_conge import DemandeConge
    from models.database import get_database
    from sqlalchemy import select
    
    # Récupérer les demandes de l'utilisateur de manière asynchrone
    async for db in get_database():
        demandes_result = await db.execute(
            select(DemandeConge).where(DemandeConge.demandeur_id == current_user.id)
        )
        demandes = demandes_result.scalars().all()
        break
    
    # Calculer le solde restant avec la méthode safe
    solde_restant = current_user.calculate_solde_conges_restant(demandes)
    
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        nom=current_user.nom,
        prenom=current_user.prenom,
        nom_complet=current_user.nom_complet,
        telephone=current_user.telephone,
        numero_piece_identite=current_user.numero_piece_identite,
        poste=current_user.poste,
        role=current_user.role,
        date_embauche=current_user.date_embauche,
        solde_conges=current_user.solde_conges,
        solde_conges_restant=solde_restant,
        departement_id=current_user.departement_id,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_verified=current_user.is_verified,
        date_naissance=current_user.date_naissance,
        nombre_enfants=current_user.nombre_enfants,
        has_medaille_honneur=current_user.has_medaille_honneur,
        genre=current_user.genre
    )

# Route pour changer le mot de passe
@router.post("/users/change-password", response_model=ChangePasswordResponse, tags=["users"])
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(fastapi_users.current_user(active=True)),
    user_manager=Depends(get_user_manager)
):
    """
    Change le mot de passe de l'utilisateur connecté
    """
    try:
        # Vérifier le mot de passe actuel
        is_valid = user_manager.password_helper.verify_and_update(
            request.current_password, current_user.hashed_password
        )[0]
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe actuel incorrect"
            )
        
        # Valider le nouveau mot de passe (au moins 6 caractères)
        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nouveau mot de passe doit contenir au moins 6 caractères"
            )
        
        # Hasher le nouveau mot de passe
        new_hashed_password = user_manager.password_helper.hash(request.new_password)
        
        # Mettre à jour le mot de passe dans la base de données
        update_dict = {"hashed_password": new_hashed_password}
        await user_manager.user_db.update(current_user, update_dict)
        
        return ChangePasswordResponse(message="Mot de passe modifié avec succès")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erreur lors du changement de mot de passe: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du changement de mot de passe"
        )

# Routes d'authentification par défaut (pour compatibilité)
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)

# Routes d'inscription
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# Routes de réinitialisation de mot de passe
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

# Routes de vérification
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
) 