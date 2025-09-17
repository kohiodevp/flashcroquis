# management/commands/initialize_qgis.py
"""
Commande pour initialiser QGIS
Usage: python manage.py initialize_qgis
"""

from django.core.management.base import BaseCommand
from ApiFlashCroquis.qgis_utils import initialize_qgis_if_needed, get_qgis_manager


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
