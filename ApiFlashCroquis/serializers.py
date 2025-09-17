# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ProjectSession, Layer, GeneratedFile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ProjectSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSession
        fields = ['session_id', 'title', 'crs', 'created_at', 'last_accessed']
        read_only_fields = ['session_id', 'created_at', 'last_accessed']

class LayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Layer
        fields = ['id', 'session', 'name', 'layer_type', 'geometry_type', 'data_source', 'feature_count', 'created_at']
        read_only_fields = ['id', 'created_at']

class GeneratedFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedFile
        fields = ['id', 'session', 'file_type', 'file_path', 'file_url', 'created_at', 'metadata']
        read_only_fields = ['id', 'file_url', 'created_at']
    
    def get_file_url(self, obj):
        return obj.get_file_url()

class RenderMapSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    width = serializers.IntegerField(default=800)
    height = serializers.IntegerField(default=600)
    dpi = serializers.IntegerField(default=96)
    format_image = serializers.CharField(default='png')
    extent = serializers.CharField(required=False, allow_blank=True)
    background_color = serializers.CharField(default='transparent')
    enable_grid = serializers.BooleanField(default=False)
    grid_interval = serializers.FloatField(default=100)
    grid_color = serializers.CharField(default='#888888')
    grid_label_font_size = serializers.IntegerField(default=8)
    grid_horizontal_labels = serializers.BooleanField(default=True)
    grid_vertical_labels = serializers.BooleanField(default=True)
    grid_label_position = serializers.ChoiceField(choices=['all', 'edges', 'corners'], default='all')
    show_points = serializers.CharField(required=False, allow_blank=True)
    enable_point_labels = serializers.BooleanField(default=False)
    label_field = serializers.CharField(default='Bornes')
    label_color = serializers.CharField(default='#000000')
    label_size = serializers.IntegerField(default=10)
    label_offset_x = serializers.IntegerField(default=0)
    label_offset_y = serializers.IntegerField(default=0)

class AddLayerSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    data_source = serializers.CharField(required=True)
    layer_name = serializers.CharField(required=False, allow_blank=True)

class GetLayerFeaturesSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    layer_id = serializers.UUIDField(required=True)
    page = serializers.IntegerField(default=1)
    limit = serializers.IntegerField(default=50)
    offset = serializers.IntegerField(default=0)

class ParcelleDetailSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    points = serializers.CharField(required=True)  # JSON string
    output_polygon_layer = serializers.CharField(required=False, allow_blank=True)
    output_points_layer = serializers.CharField(required=False, allow_blank=True)

class GenerateCroquisSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    config = serializers.DictField(required=False)
    template_id = serializers.UUIDField(required=False)
    format_croquis = serializers.CharField(default='pdf')
    output_filename = serializers.CharField(default='generated_report.pdf')

class FileUploadSerializer(serializers.Serializer):
    """Sérialiseur pour le téléchargement de fichiers"""
    # Le fichier lui-même
    file = serializers.FileField(required=True)
    
    # Session ID optionnel, si vous voulez lier le fichier à une session
    session_id = serializers.UUIDField(required=False)
    
    # Nom personnalisé pour le fichier (optionnel)
    custom_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    # Type de fichier (optionnel, pour classification)
    file_type = serializers.ChoiceField(
        choices=[
            ('unknown', 'Unknown'),
            ('vector', 'Vector Data (e.g., SHP, GeoJSON)'),
            ('raster', 'Raster Data (e.g., TIFF, JPEG)'),
            ('document', 'Document (e.g., PDF, DOCX)'),
            ('image', 'Image (e.g., PNG, JPG)'),
            ('other', 'Other')
        ],
        required=False,
        default='unknown'
    )
    
    def validate_file(self, value):
        """
        Validation personnalisée pour le fichier.
        Vous pouvez ajouter des vérifications de taille, d'extension, etc.
        """
        # Exemple: Limiter la taille du fichier à 100 Mo
        max_size = 100 * 1024 * 1024  # 100 Mo en octets
        if value.size > max_size:
            raise serializers.ValidationError(f"Le fichier est trop volumineux. Taille maximale autorisée: {max_size / (1024*1024):.2f} Mo.")
        
        # Exemple: Vérifier l'extension (facultatif)
        # allowed_extensions = ['.shp', '.geojson', '.tif', '.tiff', '.png', '.jpg', '.jpeg', '.pdf']
        # ext = os.path.splitext(value.name)[1].lower()
        # if ext not in allowed_extensions:
        #     raise serializers.ValidationError(f"Type de fichier non autorisé. Extensions autorisées: {', '.join(allowed_extensions)}")
            
        return value
