# utils.py - Utilitaires généraux pour FlashCroquis
import os
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.http import JsonResponse
from rest_framework.views import exception_handler
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Gestionnaire d'exceptions personnalisé pour l'API"""
    # Appeler le gestionnaire d'exceptions par défaut de DRF
    response = exception_handler(exc, context)

    if response is not None:
        # Formater la réponse d'erreur selon notre standard
        custom_response_data = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'error': {
                'type': exc.__class__.__name__,
                'message': str(exc),
                'details': response.data if hasattr(response, 'data') else None
            },
            'status_code': response.status_code
        }
        
        # Log de l'erreur
        logger.error(f"API Error: {exc.__class__.__name__}: {str(exc)}")
        
        response.data = custom_response_data

    return response


def cleanup_temp_files():
    """Nettoyer les fichiers temporaires anciens"""
    temp_dir = settings.FLASHCROQUIS_SETTINGS['QGIS_TEMP_DIR']
    retention_days = settings.FLASHCROQUIS_SETTINGS['TEMP_FILE_RETENTION_DAYS']
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    cleaned_count = 0
    
    try:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < cutoff_date:
                        os.remove(file_path)
                        cleaned_count += 1
                except OSError:
                    continue
                    
        logger.info(f"Cleaned up {cleaned_count} temporary files")
        return cleaned_count
        
    except Exception as e:
        logger.error(f"Error during temp file cleanup: {e}")
        return 0


def validate_file_upload(uploaded_file, allowed_extensions=None, max_size=None):
    """Valider un fichier uploadé"""
    errors = []
    
    # Vérifier l'extension
    if allowed_extensions:
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in allowed_extensions:
            errors.append(f"Extension non autorisée. Extensions acceptées: {', '.join(allowed_extensions)}")
    
    # Vérifier la taille
    if max_size and uploaded_file.size > max_size:
        errors.append(f"Fichier trop volumineux. Taille max: {max_size / (1024*1024):.1f}MB")
    
    return errors


def format_file_size(size_bytes):
    """Formater une taille de fichier en format lisible"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def health_check():
    """Vérification de santé du système"""
    checks = {}
    overall_status = True
    
    # Vérification de la base de données
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = {'status': 'ok', 'message': 'Database accessible'}
    except Exception as e:
        checks['database'] = {'status': 'error', 'message': str(e)}
        overall_status = False
    
    # Vérification du cache
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 30)
        if cache.get('health_check') == 'ok':
            checks['cache'] = {'status': 'ok', 'message': 'Cache accessible'}
        else:
            raise Exception("Cache test failed")
    except Exception as e:
        checks['cache'] = {'status': 'error', 'message': str(e)}
        overall_status = False
    
    # Vérification QGIS
    try:
        from .qgis_utils import get_qgis_manager
        manager = get_qgis_manager()
        if manager.is_initialized():
            checks['qgis'] = {'status': 'ok', 'message': 'QGIS initialized'}
        else:
            checks['qgis'] = {'status': 'warning', 'message': 'QGIS not initialized'}
    except Exception as e:
        checks['qgis'] = {'status': 'error', 'message': str(e)}
        overall_status = False
    
    # Vérification de l'espace disque
    try:
        import shutil
        total, used, free = shutil.disk_usage(settings.MEDIA_ROOT)
        free_gb = free / (1024**3)
        if free_gb < 1.0:  # Moins de 1GB libre
            checks['disk_space'] = {'status': 'warning', 'message': f'Low disk space: {free_gb:.2f}GB free'}
            overall_status = False
        else:
            checks['disk_space'] = {'status': 'ok', 'message': f'Disk space: {free_gb:.2f}GB free'}
    except Exception as e:
        checks['disk_space'] = {'status': 'error', 'message': str(e)}
    
    return {
        'overall_status': 'healthy' if overall_status else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'checks': checks
    }


# management/commands/cleanup_old_sessions.py
"""
Commande de gestion Django pour nettoyer les anciennes sessions
Usage: python manage.py cleanup_old_sessions
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from flashcroquis.models import ProjectSession, GeneratedFile


class Command(BaseCommand):
    help = 'Nettoie les sessions et fichiers anciens'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Nombre de jours avant suppression (défaut: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulation sans suppression réelle'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(f"Recherche des sessions inactives depuis plus de {days} jours...")

        # Nettoyer les sessions anciennes
        old_sessions = ProjectSession.objects.filter(
            last_accessed__lt=cutoff_date,
            status='inactive'
        )
        
        sessions_count = old_sessions.count()
        
        if dry_run:
            self.stdout.write(f"[DRY RUN] {sessions_count} sessions seraient supprimées")
        else:
            deleted_sessions, _ = old_sessions.delete()
            self.stdout.write(f"{deleted_sessions} sessions supprimées")

        # Nettoyer les fichiers générés anciens
        old_files = GeneratedFile.objects.filter(
            created_at__lt=cutoff_date
        )
        
        files_count = old_files.count()
        
        if dry_run:
            self.stdout.write(f"[DRY RUN] {files_count} fichiers générés seraient supprimés")
        else:
            # Supprimer les fichiers du système de fichiers
            for file_obj in old_files:
                try:
                    if file_obj.file_path and file_obj.file_path.storage.exists(file_obj.file_path.name):
                        file_obj.file_path.delete()
                except Exception as e:
                    self.stdout.write(f"Erreur lors de la suppression du fichier {file_obj.filename}: {e}")
            
            deleted_files, _ = old_files.delete()
            self.stdout.write(f"{deleted_files} fichiers générés supprimés")

        # Nettoyer les fichiers temporaires
        from flashcroquis.utils import cleanup_temp_files
        temp_cleaned = cleanup_temp_files()
        self.stdout.write(f"{temp_cleaned} fichiers temporaires supprimés")

        self.stdout.write(self.style.SUCCESS("Nettoyage terminé avec succès"))


# management/commands/initialize_qgis.py
"""
Commande pour initialiser QGIS
Usage: python manage.py initialize_qgis
"""

from django.core.management.base import BaseCommand
from flashcroquis.qgis_utils import initialize_qgis_if_needed, get_qgis_manager


class Command(BaseCommand):
    help = 'Initialise QGIS et vérifie la configuration'

    def handle(self, *args, **options):
        self.stdout.write("Initialisation de QGIS...")
        
        success, error = initialize_qgis_if_needed()
        
        if success:
            manager = get_qgis_manager()
            classes = manager.get_classes()
            
            self.stdout.write(self.style.SUCCESS("QGIS initialisé avec succès"))
            self.stdout.write(f"Classes QGIS disponibles: {len(classes)}")
            
            # Afficher quelques informations sur QGIS
            try:
                qgis_version = classes['Qgis'].QGIS_VERSION
                self.stdout.write(f"Version QGIS: {qgis_version}")
            except Exception as e:
                self.stdout.write(f"Impossible de récupérer la version QGIS: {e}")
                
        else:
            self.stdout.write(self.style.ERROR(f"Erreur d'initialisation QGIS: {error}"))
            
            # Afficher les erreurs détaillées
            manager = get_qgis_manager()
            for err in manager.get_errors():
                self.stdout.write(self.style.ERROR(f"  - {err}"))


# management/commands/generate_sample_data.py
"""
Commande pour générer des données de test
Usage: python manage.py generate_sample_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from flashcroquis.models import ProjectSession, Layer, Parcelle, PointSommet
import uuid


class Command(BaseCommand):
    help = 'Génère des données de test pour FlashCroquis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Nombre d\'éléments à créer (défaut: 5)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Créer un utilisateur de test si nécessaire
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@flashcroquis.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f"Utilisateur de test créé: {user.username}")

        # Créer des sessions de projet
        for i in range(count):
            session = ProjectSession.objects.create(
                title=f'Projet Test {i+1}',
                user=user,
                crs='EPSG:4326',
                status='active'
            )
            
            # Créer des couches pour chaque session
            layer = Layer.objects.create(
                session=session,
                qgis_layer_id=f'layer_{uuid.uuid4()}',
                name=f'Couche Test {i+1}',
                layer_type='vector',
                geometry_type='polygon',
                crs='EPSG:4326',
                feature_count=10 + i,
                is_visible=True
            )
            
            # Créer une parcelle pour chaque couche
            parcelle = Parcelle.objects.create(
                id=f'PARC{i+1:04d}',
                session=session,
                layer=layer,
                nom=f'Parcelle Test {i+1}',
                superficie=1000.0 + i * 100,
                proprietaire=f'Propriétaire {i+1}',
                localisation=f'Zone {chr(65+i)}',
                status='active'
            )
            
            # Créer des points sommets pour chaque parcelle
            for j in range(4):  # 4 points pour faire un rectangle
                PointSommet.objects.create(
                    parcelle=parcelle,
                    nom_borne=f'B{j+1}',
                    x=10.0 + i + j * 0.001,
                    y=12.0 + i + j * 0.001,
                    ordre=j,
                    distance=50.0 + j * 10
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Données de test générées avec succès:\n'
                f'- {count} sessions de projet\n'
                f'- {count} couches\n'
                f'- {count} parcelles\n'
                f'- {count * 4} points sommets'
            )
        )


# Exemple de fichier de migration initial
MIGRATION_CONTENT = '''
# Generated migration for FlashCroquis models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(default='Nouveau Projet', max_length=255)),
                ('crs', models.CharField(default='EPSG:4326', max_length=50)),
                ('project_file', models.FileField(blank=True, null=True, upload_to='projects/')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('error', 'Error')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_accessed', models.DateTimeField(auto_now=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'project_sessions',
                'ordering': ['-last_accessed'],
            },
        ),
        migrations.CreateModel(
            name='Layer',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('qgis_layer_id', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('layer_type', models.CharField(choices=[('vector', 'Vector'), ('raster', 'Raster'), ('unknown', 'Unknown')], max_length=20)),
                ('geometry_type', models.CharField(blank=True, choices=[('point', 'Point'), ('line', 'Line'), ('polygon', 'Polygon'), ('unknown', 'Unknown')], max_length=20, null=True)),
                ('source_file', models.FileField(blank=True, null=True, upload_to='layers/')),
                ('source_url', models.URLField(blank=True, null=True)),
                ('crs', models.CharField(blank=True, max_length=50, null=True)),
                ('feature_count', models.IntegerField(default=0)),
                ('extent', models.JSONField(blank=True, default=dict)),
                ('is_visible', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='layers', to='flashcroquis.projectsession')),
            ],
            options={
                'db_table': 'layers',
                'ordering': ['created_at'],
            },
        ),
        # ... autres modèles seraient ajoutés ici
    ]
'''