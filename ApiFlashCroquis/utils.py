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