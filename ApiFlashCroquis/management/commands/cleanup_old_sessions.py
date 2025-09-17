# management/commands/cleanup_old_sessions.py
"""
Commande de gestion Django pour nettoyer les anciennes sessions
Usage: python manage.py cleanup_old_sessions
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ApiFlashCroquis.models import ProjectSession, GeneratedFile


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
        from ApiFlashCroquis.utils import cleanup_temp_files
        temp_cleaned = cleanup_temp_files()
        self.stdout.write(f"{temp_cleaned} fichiers temporaires supprimés")

        self.stdout.write(self.style.SUCCESS("Nettoyage terminé avec succès"))

