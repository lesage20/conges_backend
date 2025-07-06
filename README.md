# API Gestion des Congés

API FastAPI pour la gestion des congés avec authentification et système de rôles.

## 🚀 Fonctionnalités

- **Authentification JWT** avec FastAPIUsers
- **Système de rôles** (Employé, Chef de Service, DRH)
- **Gestion des utilisateurs** avec hiérarchie
- **Gestion des départements**
- **Gestion des demandes de congés** avec workflow de validation
- **Permissions granulaires** par rôle
- **Base de données SQLite** avec SQLAlchemy async
- **Documentation automatique** avec Swagger UI

## 📋 Prérequis

- Python 3.11+
- uv (gestionnaire de packages)

## 🛠️ Installation

1. **Cloner le projet et aller dans le dossier backend :**
```bash
cd backend
```

2. **Installer les dépendances avec uv :**
```bash
uv sync
```

3. **Activer l'environnement virtuel :**
```bash
# Windows
uv run activate

# Linux/Mac
source .venv/bin/activate
```

4. **Créer l'utilisateur admin et les données d'exemple :**
```bash
uv run python utils/create_admin.py
```

5. **Lancer le serveur de développement :**
```bash
uv run python main.py
```

L'API sera disponible à l'adresse : `http://localhost:6500`

## 📚 Documentation API

- **Swagger UI** : http://localhost:6500/docs
- **ReDoc** : http://localhost:6500/redoc

## 🔐 Authentification

### Utilisateurs de test créés automatiquement :

| Email | Mot de passe | Rôle | Département |
|-------|--------------|------|-------------|
| `admin@company.com` | `admin123` | DRH | Direction RH |
| `chef.dev@company.com` | `chef123` | Chef de Service | Développement |
| `dev1@company.com` | `dev123` | Employé | Développement |
| `marketing@company.com` | `marketing123` | Chef de Service | Marketing |

### Connexion :

```bash
# POST /api/auth/jwt/login
curl -X POST "http://localhost:6500/api/auth/jwt/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@company.com&password=admin123"
```

Réponse :
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

## 🛣️ Endpoints principaux

### Authentification
- `POST /api/auth/jwt/login` - Connexion
- `POST /api/auth/jwt/logout` - Déconnexion
- `POST /api/auth/register` - Inscription

### Utilisateurs
- `GET /api/users/me` - Profil utilisateur connecté
- `GET /api/users/equipe` - Mon équipe (Chef de service/DRH)
- `GET /api/users/managers` - Liste des managers (DRH)
- `PUT /api/users/{user_id}/role` - Modifier le rôle (DRH)

### Départements
- `GET /api/departements/` - Liste des départements
- `POST /api/departements/` - Créer un département (DRH)
- `PUT /api/departements/{id}` - Modifier un département (DRH)
- `GET /api/departements/{id}/stats` - Statistiques du département

### Demandes de congés
- `GET /api/demandes-conges/` - Liste des demandes (filtrées par rôle)
- `POST /api/demandes-conges/` - Créer une demande
- `GET /api/demandes-conges/mes-demandes` - Mes demandes
- `GET /api/demandes-conges/en-attente` - Demandes en attente (Manager/DRH)
- `POST /api/demandes-conges/{id}/valider` - Valider/refuser une demande
- `GET /api/demandes-conges/stats/dashboard` - Statistiques dashboard

## 🎭 Système de rôles

### Employé (`employe`)
- Voir ses propres demandes de congés
- Créer de nouvelles demandes
- Modifier ses demandes en attente
- Voir la liste des départements

### Chef de Service (`chef_service`)
- Toutes les permissions d'un employé
- Voir les demandes de son équipe
- Valider/refuser les demandes de son équipe
- Voir les statistiques de son équipe

### DRH (`drh`)
- Toutes les permissions d'un chef de service
- Voir toutes les demandes de congés
- Gérer les utilisateurs (rôles, affectations)
- Gérer les départements (CRUD)
- Valider toutes les demandes

## 🗃️ Structure de la base de données

### Tables principales :
- `users` - Utilisateurs avec rôles et hiérarchie
- `departements` - Départements de l'entreprise
- `demandes_conges` - Demandes de congés avec workflow

### Relations :
- User ↔ Departement (Many-to-One)
- User ↔ User (Manager/Employés)
- DemandeConge ↔ User (Demandeur)
- DemandeConge ↔ User (Valideur)

## 🧪 Tests

### Test rapide avec curl :

```bash
# 1. Se connecter
TOKEN=$(curl -s -X POST "http://localhost:6500/api/auth/jwt/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@company.com&password=admin123" | \
  jq -r '.access_token')

# 2. Récupérer son profil
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:6500/api/users/me"

# 3. Voir les départements
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:6500/api/departements/"

# 4. Créer une demande de congé
curl -X POST "http://localhost:6500/api/demandes-conges/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type_conge": "conges_payes",
    "date_debut": "2024-07-01",
    "date_fin": "2024-07-05",
    "nombre_jours": "5",
    "motif": "Vacances d été"
  }'
```

## 🔧 Configuration

### Variables d'environnement (optionnel) :
```bash
# Base de données
DATABASE_URL=sqlite+aiosqlite:///./conges.db

# JWT
SECRET_KEY=your-secret-key-here

# CORS
FRONTEND_URL=http://localhost:5173
```

## 📁 Structure du projet

```
backend/
├── models/           # Modèles SQLAlchemy et schémas Pydantic
├── routes/           # Endpoints API organisés par domaine
├── utils/            # Utilitaires (auth, dépendances)
├── middlewares/      # Middlewares personnalisés
├── views/            # (Réservé pour futures vues)
├── main.py           # Application FastAPI principale
└── requirements.txt  # Dépendances Python
```

## 🚀 Déploiement

Pour la production :

1. **Changer le SECRET_KEY** dans `utils/auth.py`
2. **Configurer une vraie base de données** (PostgreSQL recommandé)
3. **Utiliser un serveur ASGI** comme Gunicorn + Uvicorn
4. **Configurer HTTPS** et les CORS appropriés

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push sur la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

## 📝 License

Ce projet est sous licence MIT.
