# views.py
import os
import logging
from datetime import datetime
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    ProjectSession, Layer, Parcelle, PointSommet, GeneratedFile,
    ProcessingJob, QRCodeScan, LayerStyle, MapRender
)
from .serializers import (
    ProjectSessionSerializer, LayerSerializer, ParcelleSerializer,
    GeneratedFileSerializer, ProcessingJobSerializer, QRCodeScanSerializer,
    MapRenderSerializer, AddVectorLayerSerializer, AddRasterLayerSerializer,
    RemoveLayerSerializer, ZoomToLayerSerializer, ExecuteProcessingSerializer,
    RenderMapSerializer, GenerateAdvancedPDFSerializer, GenerateCroquisSerializer,
    SaveProjectSerializer, LoadProjectSerializer, StandardResponseSerializer,
    LayerInfoSerializer, ExtentInfoSerializer, HealthCheckSerializer,
    QgisInfoSerializer, PaginationSerializer
)
from .qgis_utils import (
    get_qgis_manager, initialize_qgis_if_needed, get_project_session,
    format_layer_info, format_project_info, create_polygon_with_vertex_points,
    create_print_layout_with_qgs, create_print_layout_croquis, generate_pdf_from_layout
)

logger = logging.getLogger(__name__)


class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'per_page'
    max_page_size = 100


def standard_response(success, data=None, message=None, error=None, status_code=200, metadata=None):
    """Format de réponse standardisé avec métadonnées enrichies"""
    response_data = {
        'success': success,
        'timestamp': datetime.now().isoformat(),
        'data': data,
        'message': message,
        'error': error,
        'metadata': metadata or {}
    }
    return Response(response_data, status=status_code)


def handle_exception(e, context, message):
    """Gestion centralisée des exceptions"""
    logger.error(f"Erreur dans {context}: {e}")
    return standard_response(
        success=False,
        error={
            "type": type(e).__name__,
            "message": str(e),
            "context": context
        },
        message=message,
        status_code=500
    )


class ProjectSessionViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les sessions de projet QGIS"""
    queryset = ProjectSession.objects.all()
    serializer_class = ProjectSessionSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPagination
    
    def create(self, request, *args, **kwargs):
        """Créer un nouveau projet QGIS avec session persistante"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False, 
                    error=error, 
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            # Créer la session
            session = serializer.save()
            
            # Initialiser le projet QGIS
            manager = get_qgis_manager()
            classes = manager.get_classes()
            QgsProject = classes['QgsProject']
            
            # Obtenir le projet pour cette session
            project = session.get_project(QgsProject) if hasattr(session, 'get_project') else QgsProject()
            project.setTitle(session.title)
            
            return standard_response(
                success=True,
                data=serializer.data,
                message="Projet créé avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "create_project", "Impossible de créer le projet")
    
    @action(detail=True, methods=['post'])
    def load_project(self, request, pk=None):
        """Charger un projet QGIS existant dans une session"""
        try:
            session = self.get_object()
            serializer = LoadProjectSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            project_path = serializer.validated_data['project_path']
            
            if not os.path.exists(project_path):
                return standard_response(
                    success=False,
                    error="project_path not found",
                    message=f"Fichier projet non trouvé : {project_path}",
                    status_code=404
                )
            
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False, 
                    error=error, 
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            # Logic to load QGIS project would go here
            session.project_file = project_path
            session.save()
            
            return standard_response(
                success=True,
                data=ProjectSessionSerializer(session).data,
                message="Projet chargé avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "load_project", "Impossible de charger le projet")
    
    @action(detail=True, methods=['post'])
    def save_project(self, request, pk=None):
        """Sauvegarder le projet de la session courante"""
        try:
            session = self.get_object()
            serializer = SaveProjectSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            project_path = serializer.validated_data.get('project_path')
            if not project_path:
                project_path = os.path.join(settings.MEDIA_ROOT, f'{session.id}.qgs')
            
            # Logic to save QGIS project would go here
            session.project_file = project_path
            session.save()
            
            return standard_response(
                success=True,
                data={
                    "session_id": str(session.id),
                    "file_path": project_path,
                    "saved_at": datetime.now().isoformat()
                },
                message="Projet sauvegardé avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "save_project", "Impossible de sauvegarder le projet")


class LayerViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les couches QGIS"""
    serializer_class = LayerSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        queryset = Layer.objects.all()
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        return queryset
    
    @action(detail=False, methods=['post'])
    def add_vector(self, request):
        """Ajouter une couche vectorielle"""
        try:
            serializer = AddVectorLayerSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            session = get_object_or_404(ProjectSession, id=data['session_id'])
            
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            # Logic to add vector layer would go here
            layer = Layer.objects.create(
                session=session,
                name=data['layer_name'],
                layer_type='vector',
                source_url=data.get('data_source'),
                qgis_layer_id=f"layer_{datetime.now().timestamp()}"
            )
            
            return standard_response(
                success=True,
                data=LayerSerializer(layer).data,
                message=f"Couche vectorielle '{layer.name}' ajoutée avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "add_vector_layer", "Impossible d'ajouter la couche vectorielle")
    
    @action(detail=False, methods=['post'])
    def add_raster(self, request):
        """Ajouter une couche raster"""
        try:
            serializer = AddRasterLayerSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            session = get_object_or_404(ProjectSession, id=data['session_id'])
            
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            # Logic to add raster layer would go here
            layer = Layer.objects.create(
                session=session,
                name=data['layer_name'],
                layer_type='raster',
                source_url=data.get('data_source'),
                qgis_layer_id=f"layer_{datetime.now().timestamp()}"
            )
            
            return standard_response(
                success=True,
                data=LayerSerializer(layer).data,
                message=f"Couche raster '{layer.name}' ajoutée avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "add_raster_layer", "Impossible d'ajouter la couche raster")
    
    @action(detail=True, methods=['delete'])
    def remove_layer(self, request, pk=None):
        """Supprimer une couche"""
        try:
            layer = self.get_object()
            layer_name = layer.name
            layer.delete()
            
            return standard_response(
                success=True,
                data={"layer_id": pk},
                message=f"Couche '{layer_name}' supprimée avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "remove_layer", "Impossible de supprimer la couche")
    
    @action(detail=True, methods=['get'])
    def features(self, request, pk=None):
        """Obtenir les caractéristiques d'une couche avec pagination"""
        try:
            layer = self.get_object()
            offset = int(request.query_params.get('offset', 0))
            limit = int(request.query_params.get('limit', 100))
            
            # Logic to fetch features would go here
            # This is a mock response
            features_data = {
                'layer_id': str(layer.id),
                'layer_name': layer.name,
                'total_features': layer.feature_count,
                'requested_features': min(limit, layer.feature_count - offset),
                'offset': offset,
                'limit': limit,
                'has_more': offset + limit < layer.feature_count,
                'features': []  # Would contain actual feature data
            }
            
            return standard_response(
                success=True,
                data=features_data,
                message=f"Features récupérés pour la couche '{layer.name}'"
            )
            
        except Exception as e:
            return handle_exception(e, "get_layer_features", "Impossible de récupérer les features")
    
    @action(detail=True, methods=['get'])
    def extent(self, request, pk=None):
        """Obtenir l'étendue géographique d'une couche"""
        try:
            layer = self.get_object()
            
            extent_info = {
                'layer_id': str(layer.id),
                'layer_name': layer.name,
                'coordinate_system': layer.crs,
                'extent': layer.extent,
                'bounds': layer.extent  # Would be processed bounds
            }
            
            return standard_response(
                success=True,
                data=extent_info,
                message=f"Étendue de la couche '{layer.name}' récupérée"
            )
            
        except Exception as e:
            return handle_exception(e, "get_layer_extent", "Impossible de récupérer l'étendue")
    
    @action(detail=True, methods=['post'])
    def zoom_to(self, request, pk=None):
        """Zoomer sur une couche"""
        try:
            layer = self.get_object()
            
            extent_info = {
                'layer_id': str(layer.id),
                'layer_name': layer.name,
                'extent': layer.extent
            }
            
            return standard_response(
                success=True,
                data=extent_info,
                message=f"Zoom sur la couche '{layer.name}' effectué"
            )
            
        except Exception as e:
            return handle_exception(e, "zoom_to_layer", "Impossible de zoomer sur la couche")


class ParcelleViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les parcelles cadastrales"""
    serializer_class = ParcelleSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        queryset = Parcelle.objects.all()
        session_id = self.request.query_params.get('session_id')
        search = self.request.query_params.get('search', '')
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        if search:
            queryset = queryset.filter(nom__icontains=search)
            
        return queryset


class GeneratedFileViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les fichiers générés"""
    serializer_class = GeneratedFileSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        queryset = GeneratedFile.objects.all()
        session_id = self.request.query_params.get('session_id')
        file_type = self.request.query_params.get('type')
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        if file_type and file_type != 'all':
            queryset = queryset.filter(file_type=file_type)
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Télécharger un fichier généré"""
        try:
            file_obj = self.get_object()
            if not file_obj.file_path or not os.path.exists(file_obj.file_path.path):
                return standard_response(
                    success=False,
                    error="File not found",
                    message="Fichier non trouvé",
                    status_code=404
                )
            
            response = FileResponse(
                open(file_obj.file_path.path, 'rb'),
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{file_obj.filename}"'
            return response
            
        except Exception as e:
            return handle_exception(e, "download_file", "Impossible de télécharger le fichier")


class ProcessingJobViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les tâches de traitement QGIS"""
    serializer_class = ProcessingJobSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        queryset = ProcessingJob.objects.all()
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        return queryset
    
    @action(detail=False, methods=['post'])
    def execute(self, request):
        """Exécuter un algorithme de traitement"""
        try:
            serializer = ExecuteProcessingSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            session = None
            if data.get('session_id'):
                session = get_object_or_404(ProjectSession, id=data['session_id'])
            
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            # Create processing job
            job = ProcessingJob.objects.create(
                session=session,
                algorithm_name=data['algorithm'],
                parameters=data['parameters'],
                status='pending'
            )
            
            # Mock processing execution
            job.status = 'completed'
            job.started_at = datetime.now()
            job.completed_at = datetime.now()
            job.result = {'mock': 'result'}
            job.save()
            
            return standard_response(
                success=True,
                data=ProcessingJobSerializer(job).data,
                message="Algorithme exécuté avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "execute_processing", "Impossible d'exécuter l'algorithme")


class QRCodeScanViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les scans de QR codes"""
    queryset = QRCodeScan.objects.all()
    serializer_class = QRCodeScanSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPagination


class MapRenderViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les rendus de carte"""
    serializer_class = MapRenderSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        queryset = MapRender.objects.all()
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        return queryset
    
    @action(detail=False, methods=['post'])
    def render(self, request):
        """Générer un rendu de carte"""
        try:
            serializer = RenderMapSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            session = get_object_or_404(ProjectSession, id=data['session_id'])
            
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            # Logic to render map would go here
            # This would return an HttpResponse with image data
            
            # Mock response for now
            return HttpResponse(
                b'mock_image_data',
                content_type=f"image/{data['format_image']}"
            )
            
        except Exception as e:
            return handle_exception(e, "render_map", "Impossible de générer le rendu")


# API Views spécialisées
@api_view(['POST'])
@permission_classes([AllowAny])
@swagger_auto_schema(
    request_body=GenerateAdvancedPDFSerializer,
    responses={200: StandardResponseSerializer}
)
def generate_advanced_pdf(request):
    """Générer un PDF avancé avec QgsPrintLayout"""
    try:
        serializer = GenerateAdvancedPDFSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        session = get_object_or_404(ProjectSession, id=data['session_id'])
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False,
                error=error,
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Logic to generate PDF would go here
        output_path = os.path.join(settings.MEDIA_ROOT, data['output_filename'])
        
        # Create generated file record
        generated_file = GeneratedFile.objects.create(
            session=session,
            filename=data['output_filename'],
            file_type='pdf',
            size_bytes=0,  # Would be set after generation
            generation_config=data['layout_config']
        )
        
        return standard_response(
            success=True,
            data=GeneratedFileSerializer(generated_file).data,
            message="PDF généré avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "generate_advanced_pdf", "Impossible de générer le PDF")


@api_view(['POST'])
@permission_classes([AllowAny])
@swagger_auto_schema(
    request_body=GenerateCroquisSerializer,
    responses={200: StandardResponseSerializer}
)
def generate_croquis(request):
    """Générer un croquis avec options avancées"""
    try:
        serializer = GenerateCroquisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        session = get_object_or_404(ProjectSession, id=data['session_id'])
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False,
                error=error,
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Logic to generate croquis would go here
        generated_file = GeneratedFile.objects.create(
            session=session,
            filename=data['output_filename'],
            file_type='pdf',
            size_bytes=0,
            generation_config=data['config']
        )
        
        return standard_response(
            success=True,
            data=GeneratedFileSerializer(generated_file).data,
            message="Croquis généré avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "generate_croquis", "Impossible de générer le croquis")


@api_view(['POST'])
@permission_classes([AllowAny])
@swagger_auto_schema(
    request_body=QRCodeScanSerializer,
    responses={200: StandardResponseSerializer}
)
def qr_scanner(request):
    """Scanner et traiter un QR code"""
    try:
        serializer = QRCodeScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        qr_scan = serializer.save()
        
        return standard_response(
            success=True,
            data=QRCodeScanSerializer(qr_scan).data,
            message="QR code scanné et traité avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "qr_scanner", "Impossible de scanner le QR code")


# API Views d'information système
@api_view(['GET'])
@permission_classes([AllowAny])
@swagger_auto_schema(responses={200: HealthCheckSerializer})
def health_check(request):
    """Vérification de santé de l'API"""
    return standard_response(
        success=True,
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "qgis_ready": get_qgis_manager().is_initialized()
        },
        message="Service opérationnel"
    )


@api_view(['GET'])
@permission_classes([AllowAny])
@swagger_auto_schema(responses={200: StandardResponseSerializer})
def ping(request):
    """Endpoint de test pour vérifier que le service est actif"""
    manager = get_qgis_manager()
    return standard_response(
        success=True,
        data={
            "status": "ok",
            "service": "FlashCroquis API",
            "version": "1.0.0",
            "qgis_initialized": manager.is_initialized()
        },
        message="Service en ligne et opérationnel"
    )


@api_view(['GET'])
@permission_classes([AllowAny])
@swagger_auto_schema(responses={200: QgisInfoSerializer})
def qgis_info(request):
    """Informations détaillées sur la configuration QGIS"""
    try:
        manager = get_qgis_manager()
        if not manager.is_initialized():
            success, error = manager.initialize()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
        
        # Mock QGIS info - would be replaced with actual QGIS data
        info = {
            "qgis_version": "3.22.0",
            "qgis_version_int": 32200,
            "qgis_version_name": "Białowieża",
            "status": "initialized",
            "algorithms_count": 150,
            "initialization_time": datetime.now().isoformat()
        }
        
        return standard_response(
            success=True,
            data=info,
            message="Informations QGIS récupérées avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "qgis_info", "Impossible de récupérer les informations QGIS")


@api_view(['GET'])
@permission_classes([AllowAny])
def list_files(request):
    """Lister les fichiers dans le répertoire MEDIA"""
    try:
        directory = request.GET.get('directory', '')
        file_type = request.GET.get('type', 'all')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        # Logic to list files would go here
        # This is a mock response
        files_data = {
            'files': [],
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_count': 0,
                'total_pages': 1,
                'has_next': False,
                'has_previous': False
            }
        }
        
        return standard_response(
            success=True,
            data=files_data,
            message="Fichiers récupérés avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "list_files", "Impossible de lister les fichiers")