# models.py
import os
import uuid
import json
from datetime import datetime
from django.db import models
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib.auth.models import User


class ProjectSession(models.Model):
    """Modèle pour gérer les sessions de projet QGIS persistantes"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default='Nouveau Projet')
    crs = models.CharField(max_length=50, default='EPSG:4326')
    project_file = models.FileField(upload_to='projects/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'project_sessions'
        ordering = ['-last_accessed']
    
    def __str__(self):
        return f"Session {self.id} - {self.title}"


class Layer(models.Model):
    """Modèle pour gérer les couches dans les projets"""
    
    LAYER_TYPES = [
        ('vector', 'Vector'),
        ('raster', 'Raster'),
        ('unknown', 'Unknown')
    ]
    
    GEOMETRY_TYPES = [
        ('point', 'Point'),
        ('line', 'Line'),
        ('polygon', 'Polygon'),
        ('unknown', 'Unknown')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, related_name='layers')
    qgis_layer_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    layer_type = models.CharField(max_length=20, choices=LAYER_TYPES)
    geometry_type = models.CharField(max_length=20, choices=GEOMETRY_TYPES, null=True, blank=True)
    source_file = models.FileField(upload_to='layers/', null=True, blank=True)
    source_url = models.URLField(null=True, blank=True)
    crs = models.CharField(max_length=50, null=True, blank=True)
    feature_count = models.IntegerField(default=0)
    extent = models.JSONField(default=dict, blank=True)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'layers'
        unique_together = ['session', 'qgis_layer_id']
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.name} ({self.layer_type})"


class Parcelle(models.Model):
    """Modèle pour les parcelles cadastrales"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('en_cours', 'En cours')
    ]
    
    id = models.CharField(max_length=50, primary_key=True)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, related_name='parcelles')
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, null=True, blank=True)
    nom = models.CharField(max_length=255)
    superficie = models.FloatField()
    proprietaire = models.CharField(max_length=255, null=True, blank=True)
    localisation = models.CharField(max_length=255, null=True, blank=True)
    adresse = models.TextField(null=True, blank=True)
    geometry = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'parcelles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.id} - {self.nom}"


class PointSommet(models.Model):
    """Modèle pour les points sommets des parcelles"""
    
    parcelle = models.ForeignKey(Parcelle, on_delete=models.CASCADE, related_name='points_sommets')
    nom_borne = models.CharField(max_length=10)  # B1, B2, B3, etc.
    x = models.FloatField()
    y = models.FloatField()
    distance = models.FloatField(default=0.0)
    ordre = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'points_sommets'
        unique_together = ['parcelle', 'ordre']
        ordering = ['parcelle', 'ordre']
    
    def __str__(self):
        return f"{self.parcelle.id} - {self.nom_borne}"


class GeneratedFile(models.Model):
    """Modèle pour gérer les fichiers générés (PDF, images, etc.)"""
    
    FILE_TYPES = [
        ('pdf', 'PDF'),
        ('png', 'PNG'),
        ('jpg', 'JPEG'),
        ('qgs', 'QGIS Project'),
        ('other', 'Other')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, related_name='generated_files')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    file_path = models.FileField(upload_to='generated/')
    size_bytes = models.BigIntegerField(default=0)
    generation_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'generated_files'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.filename} ({self.file_type})"


class ProcessingJob(models.Model):
    """Modèle pour suivre les tâches de traitement QGIS"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, related_name='processing_jobs')
    algorithm_name = models.CharField(max_length=255)
    parameters = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'processing_jobs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Job {self.id} - {self.algorithm_name}"


class QRCodeScan(models.Model):
    """Modèle pour gérer les scans de QR codes"""
    
    DATA_TYPES = [
        ('parcelle', 'Parcelle'),
        ('document', 'Document'),
        ('unknown', 'Unknown')
    ]
    
    VALIDITY_CHOICES = [
        ('valid', 'Valid'),
        ('questionable', 'Questionable'),
        ('invalid', 'Invalid')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, null=True, blank=True)
    raw_data = models.TextField()
    data_type = models.CharField(max_length=20, choices=DATA_TYPES, default='unknown')
    validity = models.CharField(max_length=20, choices=VALIDITY_CHOICES, default='valid')
    processed_data = models.JSONField(default=dict, blank=True)
    scanned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'qr_scans'
        ordering = ['-scanned_at']
    
    def __str__(self):
        return f"QR Scan {self.id} - {self.data_type}"


class LayerStyle(models.Model):
    """Modèle pour gérer les styles des couches"""
    
    layer = models.OneToOneField(Layer, on_delete=models.CASCADE, related_name='style')
    symbol_color = models.CharField(max_length=7, default='#FF0000')  # Hex color
    symbol_size = models.FloatField(default=10.0)
    symbol_style = models.CharField(max_length=50, default='circle')
    line_width = models.FloatField(default=1.0)
    fill_color = models.CharField(max_length=7, null=True, blank=True)
    opacity = models.FloatField(default=1.0)
    show_labels = models.BooleanField(default=False)
    label_field = models.CharField(max_length=255, null=True, blank=True)
    label_color = models.CharField(max_length=7, default='#000000')
    label_size = models.IntegerField(default=10)
    label_offset_x = models.IntegerField(default=0)
    label_offset_y = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'layer_styles'
    
    def __str__(self):
        return f"Style for {self.layer.name}"


class MapRender(models.Model):
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