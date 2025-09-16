# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ProjectSession, Layer, Parcelle, PointSommet, GeneratedFile,
    ProcessingJob, QRCodeScan, LayerStyle, MapRender
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ProjectSessionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    layers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectSession
        fields = [
            'id', 'title', 'crs', 'project_file', 'status',
            'created_at', 'last_accessed', 'user', 'metadata',
            'layers_count'
        ]
        read_only_fields = ['id', 'created_at', 'last_accessed', 'user']
    
    def get_layers_count(self, obj):
        return obj.layers.count()


class LayerStyleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayerStyle
        fields = [
            'symbol_color', 'symbol_size', 'symbol_style', 'line_width',
            'fill_color', 'opacity', 'show_labels', 'label_field',
            'label_color', 'label_size', 'label_offset_x', 'label_offset_y'
        ]


class LayerSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(write_only=True)
    style = LayerStyleSerializer(read_only=True)
    
    class Meta:
        model = Layer
        fields = [
            'id', 'qgis_layer_id', 'name', 'layer_type', 'geometry_type',
            'source_file', 'source_url', 'crs', 'feature_count', 'extent',
            'is_visible', 'created_at', 'updated_at', 'session_id', 'style'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'qgis_layer_id']
    
    def create(self, validated_data):
        session_id = validated_data.pop('session_id')
        validated_data['session_id'] = session_id
        return super().create(validated_data)


class PointSommetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointSommet
        fields = ['nom_borne', 'x', 'y', 'distance', 'ordre', 'created_at']
        read_only_fields = ['created_at']


class ParcelleSerializer(serializers.ModelSerializer):
    points_sommets = PointSommetSerializer(many=True, read_only=True)
    session_id = serializers.CharField(write_only=True)
    layer_id = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Parcelle
        fields = [
            'id', 'nom', 'superficie', 'proprietaire', 'localisation',
            'adresse', 'geometry', 'status', 'created_at', 'updated_at',
            'points_sommets', 'session_id', 'layer_id'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        session_id = validated_data.pop('session_id')
        layer_id = validated_data.pop('layer_id', None)
        validated_data['session_id'] = session_id
        if layer_id:
            validated_data['layer_id'] = layer_id
        return super().create(validated_data)


class GeneratedFileSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(write_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedFile
        fields = [
            'id', 'filename', 'file_type', 'file_path', 'size_bytes',
            'generation_config', 'created_at', 'session_id', 'file_url'
        ]
        read_only_fields = ['id', 'created_at', 'size_bytes']
    
    def get_file_url(self, obj):
        if obj.file_path:
            return obj.file_path.url
        return None
    
    def create(self, validated_data):
        session_id = validated_data.pop('session_id')
        validated_data['session_id'] = session_id
        return super().create(validated_data)


class ProcessingJobSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(write_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessingJob
        fields = [
            'id', 'algorithm_name', 'parameters', 'status', 'result',
            'error_message', 'started_at', 'completed_at', 'created_at',
            'session_id', 'duration'
        ]
        read_only_fields = [
            'id', 'status', 'result', 'error_message', 'started_at',
            'completed_at', 'created_at'
        ]
    
    def get_duration(self, obj):
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None
    
    def create(self, validated_data):
        session_id = validated_data.pop('session_id')
        validated_data['session_id'] = session_id
        return super().create(validated_data)


class QRCodeScanSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = QRCodeScan
        fields = [
            'id', 'raw_data', 'data_type', 'validity', 'processed_data',
            'scanned_at', 'session_id'
        ]
        read_only_fields = ['id', 'data_type', 'validity', 'processed_data', 'scanned_at']
    
    def create(self, validated_data):
        session_id = validated_data.pop('session_id', None)
        if session_id:
            validated_data['session_id'] = session_id
        
        # Process QR data
        raw_data = validated_data['raw_data']
        validated_data['data_type'] = self._determine_data_type(raw_data)
        validated_data['validity'] = self._determine_validity(raw_data)
        validated_data['processed_data'] = self._process_data(raw_data)
        
        return super().create(validated_data)
    
    def _determine_data_type(self, data):
        if 'PARC' in data:
            return 'parcelle'
        elif 'DOC' in data:
            return 'document'
        return 'unknown'
    
    def _determine_validity(self, data):
        return 'valid' if len(data) > 5 else 'questionable'
    
    def _process_data(self, data):
        return {
            'raw_data': data,
            'data_type': self._determine_data_type(data),
            'timestamp': serializers.DateTimeField().to_representation(
                serializers.DateTimeField().to_internal_value('now')
            ),
            'validity': self._determine_validity(data)
        }


class MapRenderSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(write_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MapRender
        fields = [
            'id', 'width', 'height', 'dpi', 'format_output', 'quality',
            'background_color', 'bbox', 'scale', 'show_grid', 'grid_config',
            'render_config', 'image_file', 'created_at', 'session_id', 'image_url'
        ]
        read_only_fields = ['id', 'image_file', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image_file:
            return obj.image_file.url
        return None
    
    def create(self, validated_data):
        session_id = validated_data.pop('session_id')
        validated_data['session_id'] = session_id
        return super().create(validated_data)


# Serializers pour les opérations spécialisées
class AddVectorLayerSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    data_source = serializers.CharField(max_length=500)
    layer_name = serializers.CharField(max_length=255, default='Couche Vectorielle')
    is_parcelle = serializers.BooleanField(default=False)
    output_polygon_layer = serializers.CharField(max_length=500, required=False)
    output_points_layer = serializers.CharField(max_length=500, required=False)
    
    # Options de labeling
    enable_point_labels = serializers.BooleanField(default=False)
    label_field = serializers.CharField(max_length=100, default='Bornes')
    label_color = serializers.CharField(max_length=7, default='#000000')
    label_size = serializers.IntegerField(default=10, min_value=6, max_value=72)
    label_offset_x = serializers.IntegerField(default=0)
    label_offset_y = serializers.IntegerField(default=0)


class AddRasterLayerSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    data_source = serializers.CharField(max_length=500)
    layer_name = serializers.CharField(max_length=255, default='Couche Raster')


class RemoveLayerSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    layer_id = serializers.UUIDField()


class ZoomToLayerSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    layer_id = serializers.UUIDField()


class ExecuteProcessingSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=False)
    algorithm = serializers.CharField(max_length=255)
    parameters = serializers.JSONField(default=dict)
    output_format = serializers.ChoiceField(
        choices=['json', 'summary'],
        default='json'
    )


class RenderMapSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    width = serializers.IntegerField(default=800, min_value=100, max_value=5000)
    height = serializers.IntegerField(default=600, min_value=100, max_value=5000)
    dpi = serializers.IntegerField(default=96, min_value=72, max_value=300)
    format_image = serializers.ChoiceField(choices=['png', 'jpg', 'jpeg'], default='png')
    quality = serializers.IntegerField(default=90, min_value=1, max_value=100)
    background = serializers.CharField(max_length=20, default='transparent')
    bbox = serializers.CharField(max_length=255, required=False)
    scale = serializers.FloatField(required=False)
    
    # Points options
    show_points = serializers.CharField(required=False)
    points_style = serializers.ChoiceField(
        choices=['circle', 'square', 'triangle'],
        default='circle'
    )
    points_color = serializers.CharField(max_length=7, default='#FF0000')
    points_size = serializers.IntegerField(default=10, min_value=1, max_value=50)
    points_labels = serializers.BooleanField(default=False)
    
    # Grid options
    show_grid = serializers.BooleanField(default=False)
    grid_type = serializers.ChoiceField(
        choices=['lines', 'dots', 'crosses'],
        default='lines'
    )
    grid_spacing = serializers.FloatField(default=1.0, min_value=0.001)
    grid_color = serializers.CharField(max_length=7, default='#0000FF')
    grid_width = serializers.IntegerField(default=1, min_value=1, max_value=10)
    grid_size = serializers.IntegerField(default=3, min_value=1, max_value=20)
    grid_labels = serializers.BooleanField(default=False)
    grid_label_position = serializers.ChoiceField(
        choices=['corners', 'edges', 'all'],
        default='edges'
    )
    grid_vertical_labels = serializers.BooleanField(default=False)
    grid_label_font_size = serializers.IntegerField(default=8, min_value=6, max_value=20)


class GenerateAdvancedPDFSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    layout_config = serializers.JSONField(default=dict)
    output_filename = serializers.CharField(max_length=255, default='generated_report.pdf')


class GenerateCroquisSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    config = serializers.JSONField(default=dict)
    output_filename = serializers.CharField(max_length=255, default='croquis.pdf')


class SaveProjectSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    project_path = serializers.CharField(max_length=500, required=False)


class LoadProjectSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=False)
    project_path = serializers.CharField(max_length=500)


# Serializers pour les réponses
class StandardResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    timestamp = serializers.DateTimeField()
    data = serializers.JSONField(required=False)
    message = serializers.CharField(required=False)
    error = serializers.JSONField(required=False)
    metadata = serializers.JSONField(required=False)


class LayerInfoSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    source = serializers.CharField(required=False)
    extent = serializers.JSONField(required=False)
    feature_count = serializers.IntegerField(required=False)
    geometry_type = serializers.CharField(required=False)


class ExtentInfoSerializer(serializers.Serializer):
    layer_id = serializers.CharField()
    layer_name = serializers.CharField()
    coordinate_system = serializers.CharField(required=False)
    extent = serializers.JSONField()
    bounds = serializers.JSONField()


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    qgis_ready = serializers.BooleanField()


class QgisInfoSerializer(serializers.Serializer):
    qgis_version = serializers.CharField()
    qgis_version_int = serializers.IntegerField()
    qgis_version_name = serializers.CharField()
    status = serializers.CharField()
    algorithms_count = serializers.IntegerField()
    initialization_time = serializers.DateTimeField()


class PaginationSerializer(serializers.Serializer):
    current_page = serializers.IntegerField()
    per_page = serializers.IntegerField()
    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()