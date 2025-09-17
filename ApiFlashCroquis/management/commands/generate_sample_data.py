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
