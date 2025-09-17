# models.py
import os
import uuid
from django.db import models
from django.core.files.storage import default_storage

class ProjectSession(models.Model):
    """Modèle pour gérer une session de projet persistante"""
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default='Nouveau Projet')
    crs = models.CharField(max_length=50, default='EPSG:4326')
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} ({self.session_id})"

class Layer(models.Model):
    """Représente une couche dans un projet"""
    LAYER_TYPES = [
        ('vector', 'Vector'),
        ('raster', 'Raster'),
    ]
    
    GEOMETRY_TYPES = [
        ('point', 'Point'),
        ('line', 'Line'),
        ('polygon', 'Polygon'),
        ('unknown', 'Unknown'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, related_name='layers')
    name = models.CharField(max_length=255)
    layer_type = models.CharField(max_length=10, choices=LAYER_TYPES)
    geometry_type = models.CharField(max_length=10, choices=GEOMETRY_TYPES, null=True, blank=True)
    data_source = models.TextField()  # Chemin ou URL vers la source de données
    feature_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.layer_type})"

class GeneratedFile(models.Model):
    """Stocke les informations sur les fichiers générés"""
    FILE_TYPES = [
        ('pdf', 'PDF'),
        ('png', 'PNG'),
        ('jpg', 'JPG'),
        ('q', 'JPG'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE)
    file_type = models.CharField(max_length=5, choices=FILE_TYPES)
    file_path = models.TextField()  # Chemin absolu du fichier
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)  # Stocke des informations supplémentaires
    
    def get_file_url(self):
        """Retourne l'URL pour accéder au fichier"""
        # Implémentation dépendante de votre configuration de stockage
        return default_storage.url(self.file_path)
    
    def delete_file(self):
        """Supprime le fichier physique"""
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
    
    def __str__(self):
        return f"{self.file_type} - {self.created_at}"
    """Modèle pour gérer les rendus de carte"""
    
    FORMAT_CHOICES = [
        ('png', 'PNG'),
        ('jpg', 'JPEG')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, related_name='map_renders')
    width = models.IntegerField(default=800)
    height = models.IntegerField(default=600)
    dpi = models.IntegerField(default=96)
    format_output = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='png')
    quality = models.IntegerField(default=90)
    background_color = models.CharField(max_length=20, default='transparent')
    bbox = models.CharField(max_length=255, null=True, blank=True)
    scale = models.FloatField(null=True, blank=True)
    show_grid = models.BooleanField(default=False)
    grid_config = models.JSONField(default=dict, blank=True)
    render_config = models.JSONField(default=dict, blank=True)
    image_file = models.ImageField(upload_to='renders/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'map_renders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Render {self.id} - {self.width}x{self.height}"