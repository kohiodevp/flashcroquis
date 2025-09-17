# FlashCroquis API - Version Refactorisée

API Django REST Framework pour la gestion de projets cartographiques QGIS et la génération de documents cadastraux.

## 🏗️ Architecture Refactorisée

Cette version refactorise complètement le code original en suivant les meilleures pratiques Django/DRF :

### Structure du Projet

```
flashcroquis/
├── models.py              # Modèles Django (ORM)
├── serializers.py         # Sérialiseurs DRF
├── views.py              # ViewSets et APIViews
├── urls.py               # Configuration des routes
├── admin.py              # Interface d'administration
├── qgis_utils.py         # Utilitaires QGIS
├── utils.py              # Utilitaires généraux
├── management/
│   └── commands/         # Commandes de gestion Django
├── migrations/           # Migrations de base de données
└── tests/               # Tests unitaires
```

## 📊 Modèles de Données

### Modèles Principaux

1. **ProjectSession** - Sessions de projet QGIS persistantes
2. **Layer** - Couches vectorielles/raster
3. **Parcelle** - Parcelles cadastrales
4. **PointSommet** - Points sommets des parcelles
5. **GeneratedFile** - Fichiers générés (PDF, images)
6. **ProcessingJob** - Tâches de traitement QGIS
7. **QRCodeScan** - Scans de QR codes
8. **LayerStyle** - Styles des couches
9. **MapRender** - Rendus de cartes

## 🔌 API Endpoints

### Sessions de Projet

```http
GET    /api/v1/sessions/           # Liste des sessions
POST   /api/v1/sessions/           # Créer une session
GET    /api/v1/sessions/{id}/      # Détails d'une session
PUT    /api/v1/sessions/{id}/      # Modifier une session
DELETE /api/v1/sessions/{id}/      # Supprimer une session

POST   /api/v1/sessions/{id}/load-project/    # Charger un projet
POST   /api/v1/sessions/{id}/save-project/    # Sauvegarder un projet
```

### Couches

```http
GET    /api/v1/layers/             # Liste des couches
POST   /api/v1/layers/             # Créer une couche
GET    /api/v1/layers/{id}/        # Détails d'une couche
PUT    /api/v1/layers/{id}/        # Modifier une couche
DELETE /api/v1/layers/{id}/        # Supprimer une couche

POST   /api/v1/layers/add-vector/  # Ajouter couche vectorielle
POST   /api/v1/layers/add-raster/  # Ajouter couche raster
GET    /api/v1/layers/{id}/features/ # Features d'une couche
GET    /api/v1/layers/{id}/extent/   # Étendue d'une couche
POST   /api/v1/layers/{id}/zoom-to/  # Zoomer sur une couche
```

### Parcelles

```http
GET    /api/v1/parcelles/          # Liste des parcelles
POST   /api/v1/parcelles/          # Créer une parcelle
GET    /api/v1/parcelles/{id}/     # Détails d'une parcelle
PUT    /api/v1/parcelles/{id}/     # Modifier une parcelle
DELETE /api/v1/parcelles/{id}/     # Supprimer une parcelle
```

### Fichiers Générés

```http
GET    /api/v1/files/              # Liste des fichiers
POST   /api/v1/files/              # Créer un fichier
GET    /api/v1/files/{id}/         # Détails d'un fichier
GET    /api/v1/files/{id}/download/ # Télécharger un fichier
DELETE /api/v1/files/{id}/         # Supprimer un fichier
```

### Traitement QGIS

```http
GET    /api/v1/processing-jobs/    # Liste des tâches
POST   /api/v1/processing-jobs/execute/ # Exécuter un algorithme
GET    /api/v1/processing-jobs/{id}/ # Détails d'une tâche
```

### Rendu de Cartes

```http
GET    /api/v1/renders/            # Liste des rendus
POST   /api/v1/renders/render/     # Générer un rendu
GET    /api/v1/renders/{id}/       # Détails d'un rendu
```

### Endpoints Spécialisés

```http
POST   /api/v1/generate-pdf/       # Générer PDF avancé
POST   /api/v1/generate-croquis/   # Générer croquis
POST   /api/v1/qr-scanner/         # Scanner QR code
GET    /api/v1/health/             # Vérification santé
GET    /api/v1/ping/               # Test de connexion
GET    /api/v1/qgis-info/          # Informations QGIS
GET    /api/v1/list-files/         # Lister fichiers média
```

## 🚀 Installation et Configuration

### Prérequis

- Python 3.8+
- Django 4.2+
- QGIS 3.22+
- PostgreSQL/MySQL (recommandé) ou SQLite
- Redis (optionnel, pour le cache)

### Installation

1. **Cloner le projet**
```bash
git clone <repository-url>
cd flashcroquis
```

2. **Créer l'environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configuration de l'environnement**
```bash
cp .env.example .env
# Éditer le fichier .env avec vos paramètres
```

5. **Variables d'environnement principales**
```env
# Base
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=flashcroquis
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Redis (optionnel)
REDIS_URL=redis://localhost:6379/1

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

6. **Migrations et données initiales**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py initialize_qgis
python manage.py generate_sample_data --count 10
```

7. **Lancer le serveur**
```bash
python manage.py runserver
```

## 🔧 Configuration QGIS

### Installation QGIS

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install qgis qgis-dev python3-qgis
```

**CentOS/RHEL:**
```bash
sudo yum install qgis qgis-python qgis-dev
```

**Windows:**
Télécharger depuis [qgis.org](https://qgis.org/en/site/forusers/download.html)

### Variables d'environnement QGIS

```bash
export QGIS_PREFIX_PATH=/usr
export PYTHONPATH=${PYTHONPATH}:/usr/share/qgis/python
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib/qgis
```

## 📋 Commandes de Gestion

### Commandes personnalisées

```bash
# Initialiser QGIS
python manage.py initialize_qgis

# Nettoyer les anciennes sessions
python manage.py cleanup_old_sessions --days 7

# Générer des données de test
python manage.py generate_sample_data --count 20

# Vérification de santé complète
python manage.py check --deploy
```

## 🧪 Tests

### Lancer les tests

```bash
# Tous les tests
python manage.py test

# Tests spécifiques
python manage.py test flashcroquis.tests.test_models
python manage.py test flashcroquis.tests.test_views
python manage.py test flashcroquis.tests.test_qgis

# Avec couverture
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Structure des tests

```
flashcroquis/tests/
├── __init__.py
├── test_models.py        # Tests des modèles
├── test_serializers.py   # Tests des sérialiseurs
├── test_views.py         # Tests des vues/API
├── test_qgis_utils.py    # Tests utilitaires QGIS
├── test_admin.py         # Tests interface admin
└── fixtures/            # Données de test
```

## 📖 Documentation API

### Swagger/OpenAPI

Une fois le serveur lancé, la documentation interactive est disponible :

- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/
- **Schema JSON**: http://localhost:8000/swagger.json

### Format des réponses standardisé

Toutes les réponses API suivent le format :

```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    // Données de la réponse
  },
  "message": "Message descriptif",
  "error": null,
  "metadata": {
    // Métadonnées additionnelles
  }
}
```

## 🔒 Sécurité

### Authentication

L'API supporte plusieurs méthodes d'authentification :

1. **Session Authentication** (pour l'interface web)
2. **Token Authentication** (pour les clients API)
3. **Basic Authentication** (pour le développement)

### Permissions

- Authentification requise par défaut
- Permissions granulaires par modèle
- Validation des uploads de fichiers
- Limitation du taux de requêtes

### Headers requis

```http
Authorization: Token your-token-here
Content-Type: application/json
```

## 📊 Administration

### Interface d'administration Django

Accessible sur : http://localhost:8000/admin/

Fonctionnalités :
- Gestion complète des modèles
- Visualisation des données JSON
- Liens de téléchargement des fichiers
- Filtres et recherche avancée
- Actions en lot

### Monitoring

- Logs détaillés dans `/logs/`
- Health check endpoint : `/api/v1/health/`
- Métriques de performance
- Intégration Sentry (optionnelle)

## 🚀 Déploiement

### Docker

```dockerfile
FROM python:3.9
RUN apt-get update && apt-get install -y qgis qgis-dev
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
EXPOSE 8000
CMD ["gunicorn", "flashcroquis.wsgi:application"]
```

### Production

```bash
# Installer les dépendances de production
pip install gunicorn psycopg2-binary

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Lancer avec Gunicorn
gunicorn flashcroquis.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 300
```

### Nginx Configuration

```nginx
upstream flashcroquis {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location /static/ {
        alias /path/to/staticfiles/;
    }
    
    location /media/ {
        alias /path/to/media/;
    }
    
    location / {
        proxy_pass http://flashcroquis;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🏗️ Améliorations par rapport à l'original

### Architecture
- ✅ Séparation claire Models/Serializers/Views
- ✅ ViewSets DRF avec actions personnalisées
- ✅ Pagination automatique
- ✅ Filtres et recherche intégrés
- ✅ Interface d'administration complète

### Fonctionnalités
- ✅ Gestion persistante des sessions
- ✅ Upload et stockage des fichiers
- ✅ Système de permissions granulaires
- ✅ API de santé et monitoring
- ✅ Commandes de gestion Django

### Qualité du code
- ✅ Tests unitaires structurés
- ✅ Documentation API automatique
- ✅ Logging centralisé
- ✅ Gestion d'erreurs standardisée
- ✅ Configuration par environnement

### Performance
- ✅ Cache Redis intégré
- ✅ Requêtes optimisées (select_related, prefetch_related)
- ✅ Pagination des grandes listes
- ✅ Nettoyage automatique des fichiers temporaires

## 🔄 Migration depuis l'ancienne version

Si vous migrez depuis le code original :

1. **Sauvegarder les données existantes**
2. **Installer la nouvelle version**
3. **Adapter les appels API** (nouveaux endpoints)
4. **Migrer les fichiers** vers la nouvelle structure
5. **Tester les fonctionnalités critiques**

### Compatibilité

Les endpoints de compatibilité sont maintenus dans `urls.py` pour faciliter la migration progressive.

## 📞 Support

- **Documentation** : Consultez ce README et la documentation Swagger
- **Issues** : Créez une issue sur le repository Git
- **Tests** : Lancez la suite de tests complète avant tout déploiement

---

*Cette version refactorisée apporte une architecture robuste, maintenable et évolutive tout en conservant toutes les fonctionnalités de l'API QGIS originale.*