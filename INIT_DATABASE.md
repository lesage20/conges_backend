# 📋 Guide d'initialisation de la base de données

## 🚀 Procédure d'initialisation complète

### 1. Prérequis
- Python 3.8+
- Environnement virtuel activé
- Dépendances installées (`uv install` ou `pip install -r requirements.txt`)

### 2. Étapes d'initialisation

#### Étape 1 : Recréer la base de données (si nécessaire)
```bash
cd backend
python recreate_db.py
```
**Description** : Supprime et recrée toutes les tables avec la structure actuelle

#### Étape 2 : Initialiser avec les données de base
```bash
cd backend
python init_db.py
```
**Description** : Crée l'utilisateur administrateur et les données d'exemple

#### Étape 3 : Créer la table des notifications
```bash
cd backend
python create_notifications_table.py
```
**Description** : Crée la table des notifications avec les index nécessaires

## 🔐 Comptes par défaut créés

### Compte DRH (Administrateur)
- **Email** : `drh@entreprise.com`
- **Mot de passe** : `admin123`
- **Nom** : Caroline Dubois
- **Rôle** : DRH (Superutilisateur)
- **Département** : Direction des Ressources Humaines

### Comptes Chefs de Service
- **Développement** : `chef.dev@entreprise.com` / `chef123`
- **Marketing** : `chef.marketing@entreprise.com` / `chef123`
- **Ventes** : `chef.ventes@entreprise.com` / `chef123`

### Comptes Employés (exemples)
- **Développement** :
  - `marie.dupont@entreprise.com` / `emp123`
  - `antoine.moreau@entreprise.com` / `emp123`
  - `camille.roux@entreprise.com` / `emp123`
  - `lucas.martin@entreprise.com` / `emp123`
  
- **Marketing** :
  - `julien.bernard@entreprise.com` / `emp123`
  - `emma.leroy@entreprise.com` / `emp123`
  - `pierre.simon@entreprise.com` / `emp123`
  
- **Ventes** :
  - `sarah.blanc@entreprise.com` / `emp123`
  - `maxime.henry@entreprise.com` / `emp123`
  - `celine.petit@entreprise.com` / `emp123`
  - `david.moreau@entreprise.com` / `emp123`

- **RH** :
  - `amelie.durand@entreprise.com` / `emp123`
  - `kevin.martinez@entreprise.com` / `emp123`

## 📊 Départements créés

1. **Direction des Ressources Humaines** (Budget : 365 jours)
2. **Développement** (Budget : 300 jours)
3. **Marketing** (Budget : 250 jours)
4. **Ventes** (Budget : 280 jours)

## 🔧 Scripts disponibles

### `recreate_db.py`
- **Usage** : `python recreate_db.py`
- **But** : Supprime et recrée toutes les tables
- **Quand l'utiliser** : Après des modifications de modèles ou pour reset complet

### `init_db.py`
- **Usage** : `python init_db.py`
- **But** : Initialise avec admin et données d'exemple
- **Quand l'utiliser** : Première installation ou après recreate_db.py

### `create_notifications_table.py`
- **Usage** : `python create_notifications_table.py`
- **But** : Crée la table notifications
- **Quand l'utiliser** : Si la table notifications n'existe pas

## 📝 Commande complète d'initialisation

```bash
# Aller dans le répertoire backend
cd backend

# 1. Recréer la base de données
python recreate_db.py

# 2. Initialiser avec les données de base
python init_db.py

# 3. Créer la table des notifications
python create_notifications_table.py

# 4. Vérifier que tout fonctionne
python run.py
```

## ⚠️ Dépannage

### Erreur "Table already exists"
- Utiliser `python recreate_db.py` pour reset complet

### Erreur "Admin user already exists"
- Normal si vous relancez init_db.py, l'admin existe déjà

### Erreur de permissions
- Vérifier que vous êtes dans le bon répertoire (`cd backend`)
- Vérifier que l'environnement virtuel est activé

### Base de données corrompue
```bash
# Supprimer la base de données existante
rm -f conges.db

# Recréer complètement
python recreate_db.py
python init_db.py
python create_notifications_table.py
```

## 🎯 Prochaines étapes

1. Lancer l'application : `python run.py`
2. Se connecter avec le compte DRH
3. Créer vos propres utilisateurs via l'interface
4. Configurer les départements selon vos besoins 