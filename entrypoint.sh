#!/bin/sh
set -e

echo "📌 Génération des migrations..."
python3 manage.py makemigrations  ApiFlashCroquis

echo "📌 Application des migrations..."
python3 manage.py migrate --noinput

echo "📌 Création du superuser si nécessaire..."
python3 manage.py shell << END
from django.contrib.auth import get_user_model
import os
User = get_user_model()

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"✅ Superuser créé: {username}/{password}")
else:
    print("ℹ️ Superuser déjà existant")
END

echo "📌 Lancement du serveur Django..."
exec "$@"