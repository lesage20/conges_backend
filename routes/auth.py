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
            departement_id=user.departement_id,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_verified=user.is_verified
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
        departement_id=current_user.departement_id,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_verified=current_user.is_verified
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