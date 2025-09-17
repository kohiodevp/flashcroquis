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

initialize_qgis_if_needed()


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
            
            allowed_grid_types = ['lines', 'dots', 'crosses']
            if data['grid_config']['grid_type'] and data['grid_config']['grid_type'] not in allowed_grid_types:
                return standard_response(
                    success=False,
                    error="Unsupported grid type",
                    message=f"Types de grille supportés: {', '.join(allowed_grid_types)}",
                    status_code=400
                )
            
            allowed_label_positions = ['corners', 'edges', 'all']
            if data['grid_config']['grid_type'] and data['grid_config']['grid_label_position'] not in allowed_label_positions:
                return standard_response(
                    success=False,
                    error="Unsupported label position",
                    message=f"Positions de labels supportées: {', '.join(allowed_label_positions)}",
                    status_code=400
                )

            # Validation du bbox si fourni
            extent = None
            if data['bbox']:
                try:
                    coords = [float(x) for x in data['bbox'].split(',')]
                    if len(coords) == 4:
                        from qgis.core import QgsRectangle
                        extent = QgsRectangle(coords[0], coords[1], coords[2], coords[3])
                    else:
                        return standard_response(
                            success=False,
                            error="Invalid bbox format",
                            message="Le format bbox doit être: xmin,ymin,xmax,ymax",
                            status_code=400
                        )
                except ValueError:
                    return standard_response(
                        success=False,
                        error="Invalid bbox values",
                        message="Les coordonnées du bbox doivent être des nombres",
                        status_code=400
                    )

            manager = get_qgis_manager()
            classes = manager.get_classes()
            QgsProject = classes['QgsProject']
            QgsMapSettings = classes['QgsMapSettings']
            QgsMapRendererParallelJob = classes['QgsMapRendererParallelJob']
            QgsRectangle = classes['QgsRectangle']
        
            # Obtenir le projet pour cette session
            project = session.get_project(QgsProject)

            # Configuration du rendu
            map_settings = QgsMapSettings()
            map_settings.setOutputSize(QSize(data['width'], data['height']))
            map_settings.setOutputDpi(data['dpi'])

            # Définir le CRS
            if project.crs().isValid():
                map_settings.setDestinationCrs(project.crs())

            # Définir l'étendue
            if extent:
                # Utiliser l'étendue fournie
                map_settings.setExtent(extent)
            else:
                # Calculer l'étendue combinée des couches
                try:
                    project_extent = QgsRectangle()
                    project_extent.setMinimal()
                    
                    visible_layers = []
                    for layer in project.mapLayers().values():
                        # Ne considérer que les couches visibles
                        if layer.isValid() and not layer.extent().isEmpty():
                            visible_layers.append(layer)
                            if project_extent.isEmpty():
                                project_extent = QgsRectangle(layer.extent())
                            else:
                                project_extent.combineExtentWith(layer.extent())
                    
                    if not project_extent.isEmpty() and visible_layers:
                        # Appliquer l'échelle si spécifiée
                        if data['scale']:
                            try:
                                scale_value = float(data['scale'])
                                if scale_value > 0:
                                    # Calculer la nouvelle étendue basée sur l'échelle
                                    center_x = (project_extent.xMinimum() + project_extent.xMaximum()) / 2
                                    center_y = (project_extent.yMinimum() + project_extent.yMaximum()) / 2
                                    
                                    # Convertir l'échelle en dimensions (approximatif)
                                    # 1 unité de carte = 1 mètre à l'échelle donnée
                                    map_units_per_pixel = scale_value / (data['dpi'] * 0.0254)  # 0.0254 m/pouce
                                    new_width = data['width'] * map_units_per_pixel
                                    new_height = data['height'] * map_units_per_pixel
                                    
                                    new_extent = QgsRectangle(
                                        center_x - new_width/2,
                                        center_y - new_height/2,
                                        center_x + new_width/2,
                                        center_y + new_height/2
                                    )
                                    map_settings.setExtent(new_extent)
                                else:
                                    map_settings.setExtent(project_extent)
                            except ValueError:
                                map_settings.setExtent(project_extent)
                        else:
                            # Ajouter une marge de 5%
                            margin = 0.05
                            width_margin = (project_extent.xMaximum() - project_extent.xMinimum()) * margin
                            height_margin = (project_extent.yMaximum() - project_extent.yMinimum()) * margin
                            extended_extent = QgsRectangle(
                                project_extent.xMinimum() - width_margin,
                                project_extent.yMinimum() - height_margin,
                                project_extent.xMaximum() + width_margin,
                                project_extent.yMaximum() + height_margin
                            )
                            map_settings.setExtent(extended_extent)
                    else:
                        # Étendue par défaut si aucune couche
                        default_extent = QgsRectangle(-180, -90, 180, 90)
                        map_settings.setExtent(default_extent)
                except Exception as e:
                    logger.warning(f"Erreur lors du calcul de l'étendue: {e}")
                    # Étendue par défaut en cas d'erreur
                    default_extent = QgsRectangle(-180, -90, 180, 90)
                    map_settings.setExtent(default_extent)

            # Définir les couches visibles
            visible_layers = [layer for layer in project.mapLayers().values() if layer.isValid()]
            map_settings.setLayers(visible_layers)
            
            # Définir la couleur de fond
            if data['background_color'] != 'transparent':
                from PyQt5.QtGui import QColor
                try:
                    color = QColor(data['background_color'])
                    if color.isValid():
                        map_settings.setBackgroundColor(color)
                except Exception as e:
                    logger.warning(f"Couleur de fond invalide: {e}")
                    # Utiliser la couleur par défaut
                    map_settings.setBackgroundColor(QColor(255, 255, 255))
            else:
                # Fond transparent
                from PyQt5.QtGui import QColor
                map_settings.setBackgroundColor(QColor(0, 0, 0, 0))  # RGBA avec alpha = 0

            # Configuration du rendu avec antialiasing
            map_settings.setFlag(QgsMapSettings.Antialiasing, True)
            map_settings.setFlag(QgsMapSettings.DrawLabeling, True)
            map_settings.setFlag(QgsMapSettings.UseAdvancedEffects, True)
                
            # Choisir le format d'image approprié
            if data['format_output'] == 'png':
                image_format = QImage.Format_ARGB32 if data['background_color'] == 'transparent' else QImage.Format_RGB32
            else:  # jpg/jpeg
                image_format = QImage.Format_RGB32
            
            image = QImage(data['width'], data['height'], image_format)
            
            # Remplir l'image avec la couleur de fond
            if data['background_color'] == 'transparent' and data['format_output'] == 'png':
                image.fill(0)  # Fond transparent
            else:
                from PyQt5.QtGui import QColor
                if data['background_color'] != 'transparent':
                    color = QColor(data['background_color'])
                    if color.isValid():
                        image.fill(color)
                    else:
                        image.fill(QColor(255, 255, 255))  # Blanc par défaut
                else:
                    image.fill(QColor(255, 255, 255))
            
            # Créer un painter pour le rendu
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            
            # Rendu parallèle des couches existantes
            job = QgsMapRendererParallelJob(map_settings)
            job.start()
            job.waitForFinished()
            rendered_image = job.renderedImage()
            
            # Dessiner l'image rendue sur l'image finale
            painter.drawImage(0, 0, rendered_image)
            
            # Obtenir l'étendue de la carte pour la grille
            extent_map = map_settings.extent()
            
            # Dessiner la grille si demandé
            if data['show_grid']:
                try:
                    # Définir le style de la grille
                    grid_qcolor = QColor(data['grid_config']['grid_color'])
                    if not grid_qcolor.isValid():
                        grid_qcolor = QColor(0, 0, 255)  # Bleu par défaut
                    
                    painter.setPen(QPen(grid_qcolor, data['grid_config']['grid_width']))
                    painter.setFont(QFont('Arial', data['grid_config']['grid_label_font_size']))
                    
                    # Calculer les lignes de grille
                    x_min = extent_map.xMinimum()
                    x_max = extent_map.xMaximum()
                    y_min = extent_map.yMinimum()
                    y_max = extent_map.yMaximum()
                    
                    # Lignes verticales (méridiens)
                    x_start = (x_min // data['grid_config']['grid_spacing']) * data['grid_config']['grid_spacing']
                    x_lines = []
                    x = x_start
                    while x <= x_max:
                        if x >= x_min:
                            x_lines.append(x)
                        x += data['grid_config']['grid_spacing']
                    
                    # Lignes horizontales (parallèles)
                    y_start = (y_min // data['grid_config']['grid_spacing']) * data['grid_config']['grid_spacing']
                    y_lines = []
                    y = y_start
                    while y <= y_max:
                        if y >= y_min:
                            y_lines.append(y)
                        y += data['grid_config']['grid_spacing']
                    
                    # Dessiner selon le type de grille
                    if data['grid_config']['grid_type'] == 'lines':
                        # Grille en lignes continues
                        for x in x_lines:
                            x_pixel = int(((x - x_min) / (x_max - x_min)) * width)
                            painter.drawLine(x_pixel, 0, x_pixel, data['height'])
                        
                        for y in y_lines:
                            y_pixel = int((1 - (y - y_min) / (y_max - y_min)) * data['height'])
                            painter.drawLine(0, y_pixel, width, y_pixel)
                    
                    elif data['grid_config']['grid_type'] == 'dots':
                        # Grille en points
                        painter.setPen(QPen(data['grid_config']['grid_qcolor'], data['grid_config']['grid_width'] * 2))  # Points plus visibles
                        for x in x_lines:
                            x_pixel = int(((x - x_min) / (x_max - x_min)) * width)
                            for y in y_lines:
                                y_pixel = int((1 - (y - y_min) / (y_max - y_min)) * data['height'])
                                painter.drawPoint(x_pixel, y_pixel)
                    
                    elif data['grid_config']['grid_type'] == 'crosses':
                        # Grille en croix
                        cross_size = data['grid_config']['grid_size']
                        for x in x_lines:
                            x_pixel = int(((x - x_min) / (x_max - x_min)) * data['width'])
                            for y in y_lines:
                                y_pixel = int((1 - (y - y_min) / (y_max - y_min)) * data['height'])
                                # Ligne horizontale de la croix
                                painter.drawLine(x_pixel - cross_size, y_pixel, x_pixel + cross_size, y_pixel)
                                # Ligne verticale de la croix
                                painter.drawLine(x_pixel, y_pixel - cross_size, x_pixel, y_pixel + cross_size)
                    
                    # Dessiner les labels si demandé
                    if data['grid_config']['grid_labels']:
                        painter.setPen(QPen(data['grid_config']['grid_qcolor'], 1))
                        painter.setFont(QFont('Arial', data['grid_config']['grid_label_font_size']))
                        
                        # Labels verticaux sur les bords gauche et droit si activé
                        if data['grid_config']['grid_vertical_labels']:
                            for j, y in enumerate(y_lines):
                                y_pixel = int((1 - (y - y_min) / (y_max - y_min)) * height)
                                
                                # Déterminer si on doit afficher le label selon la position demandée
                                show_label = False
                                if data['grid_config']['grid_label_position'] == 'corners':
                                    # Seulement les coins
                                    if j == 0 or j == len(y_lines) - 1:
                                        show_label = True
                                elif data['grid_config']['grid_label_position'] == 'edges':
                                    # Bordures seulement
                                    if j == 0 or j == len(y_lines) - 1:
                                        show_label = True
                                else:  # 'all'
                                    # Tous les points
                                    show_label = True
                                
                                if show_label:
                                    label = f"{y:.2f}°"
                                    
                                    # Label à gauche
                                    text_x_left = 10
                                    text_y_left = y_pixel + grid_label_font_size//2
                                    if 0 <= text_y_left <= height:
                                        # Rotation du texte de 90 degrés
                                        painter.save()
                                        painter.translate(text_x_left, text_y_left)
                                        painter.rotate(-90)
                                        painter.drawText(0, 0, label)
                                        painter.restore()
                                    
                                    # Label à droite
                                    text_x_right = data['width'] - grid_label_font_size 
                                    text_y_right = y_pixel + grid_label_font_size//2
                                    if 0 <= text_y_right <= height:
                                        # Rotation du texte de 90 degrés
                                        painter.save()
                                        painter.translate(text_x_right, text_y_right)
                                        painter.rotate(-90)
                                        painter.drawText(0, 0, label)
                                        painter.restore()
                        
                        # Labels normaux (horizontaux) pour les lignes verticales
                        for i, x in enumerate(x_lines):
                            x_pixel = int(((x - x_min) / (x_max - x_min)) * width)
                            
                            # Déterminer si on doit afficher le label selon la position demandée
                            show_label = False
                            if data['grid_config']['grid_label_position'] == 'corners':
                                # Seulement les coins
                                if i == 0 or i == len(x_lines) - 1:
                                    show_label = True
                            elif data['grid_config']['grid_label_position'] == 'edges':
                                # Bordures seulement (haut et bas)
                                if i == 0 or i == len(x_lines) - 1:
                                    show_label = True
                            else:  # 'all'
                                # Tous les points
                                show_label = True
                            
                            if show_label:
                                label = f"{x:.2f}°"
                                
                                # Label en haut
                                text_x_top = x_pixel + 5
                                text_y_top = grid_label_font_size + 5
                                if 0 <= text_x_top <= data['width'] - 50:
                                    painter.drawText(text_x_top, text_y_top, label)
                                
                                # Label en bas
                                text_x_bottom = x_pixel + 5
                                text_y_bottom = height - 5
                                if 0 <= text_x_bottom <= data['width'] - 50:
                                    painter.drawText(text_x_bottom, text_y_bottom, label)
                        
                except Exception as e:
                    logger.warning(f"Erreur lors du dessin de la grille: {e}")
            
            # # Dessiner les points géographiques si fournis
            # if geo_points:
            #     # Convertir les coordonnées géographiques en pixels
            #     extent_map = map_settings.extent()
            #     map_width = extent_map.xMaximum() - extent_map.xMinimum()
            #     map_height = extent_map.yMaximum() - extent_map.yMinimum()
                
            #     for point_info in geo_points:
            #         x_geo = point_info['x']
            #         y_geo = point_info['y']
            #         label = point_info['label']
            #         color_hex = point_info['color']
            #         size = point_info['size']
                    
            #         # Vérifier si le point est dans l'étendue de la carte
            #         if (extent_map.xMinimum() <= x_geo <= extent_map.xMaximum() and 
            #             extent_map.yMinimum() <= y_geo <= extent_map.yMaximum()):
                        
            #             # Convertir les coordonnées géographiques en pixels
            #             x_pixel = int(((x_geo - extent_map.xMinimum()) / map_width) * width)
            #             y_pixel = int((1 - (y_geo - extent_map.yMinimum()) / map_height) * height)
                        
            #             # Dessiner le point
            #             point_color = QColor(color_hex)
            #             if point_color.isValid():
            #                 painter.setPen(QPen(point_color, 2))
            #                 painter.setBrush(QBrush(point_color))
            #             else:
            #                 painter.setPen(QPen(QColor(255, 0, 0), 2))
            #                 painter.setBrush(QBrush(QColor(255, 0, 0)))
                        
            #             # Dessiner selon le style
            #             if points_style == 'square':
            #                 painter.drawRect(x_pixel - size//2, y_pixel - size//2, size, size)
            #             elif points_style == 'triangle':
            #                 # Dessiner un triangle pointant vers le haut
            #                 points_array = [
            #                     QPoint(x_pixel, y_pixel - size//2),
            #                     QPoint(x_pixel - size//2, y_pixel + size//2),
            #                     QPoint(x_pixel + size//2, y_pixel + size//2)
            #                 ]
            #                 painter.drawPolygon(*points_array, 3)
            #             else:  # circle (par défaut)
            #                 painter.drawEllipse(x_pixel - size//2, y_pixel - size//2, size, size)
                        
            #             # Dessiner le label si demandé
            #             if points_labels and label:
            #                 painter.setPen(QPen(QColor(0, 0, 0)))
            #                 painter.setFont(QFont('Arial', max(8, size//2)))
            #                 painter.drawText(x_pixel + size, y_pixel, label)
            
            painter.end()
            
            # Convertir en bytes selon le format
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.WriteOnly)
            
            if data['format_output'] in ['jpg', 'jpeg']:
                # Pour JPEG, s'assurer qu'il n'y a pas de transparence
                if image.hasAlphaChannel():
                    # Convertir en image sans transparence
                    final_image = QImage(image.size(), QImage.Format_RGB32)
                    final_image.fill(QColor(255, 255, 255))
                    painter = QPainter(final_image)
                    painter.drawImage(0, 0, image)
                    painter.end()
                    final_image.save(buffer, "JPEG", quality)
                else:
                    image.save(buffer, "JPEG", quality)
                content_type = 'image/jpeg'
            else:
                image.save(buffer, "PNG")
                content_type = 'image/png'
            
            # Ajouter des headers pour le cache
            response = HttpResponse(byte_array.data(), content_type=content_type)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            return response
            
        except Exception as e:
            return handle_exception(e, "render_map", "Impossible de générer le rendu")


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
            'status': 'ok',
            'service': 'Flash Croquis API',
            'version': '1.0.0',
            'qgis_initialized': manager.is_initialized(),
            'uptime': datetime.now().isoformat()
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
        
        classes = manager.get_classes()
        QgsApplicationClass = classes['QgsApplication']
        Qgis = classes['Qgis']

        info = {
            'qgis_version': Qgis.QGIS_VERSION,
            'qgis_version_int': Qgis.QGIS_VERSION_INT,
            'qgis_version_name': Qgis.QGIS_RELEASE_NAME,
            'status': 'initialized' if QgsApplicationClass.instance() else 'partially_initialized',
            'algorithms_count': len(QgsApplicationClass.processingRegistry().algorithms()) if hasattr(QgsApplicationClass, 'processingRegistry') and QgsApplicationClass.instance() else 0,
            'providers_count': len(QgsApplicationClass.processingRegistry().providers()) if hasattr(QgsApplicationClass, 'processingRegistry') and QgsApplicationClass.instance() else 0,
            'processing_available': hasattr(classes['processing'], 'run'),
            'initialization_time': datetime.now().isoformat()
        }
        
        return standard_response(
            success=True,
            data=info,
            message="Informations QGIS récupérées avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "qgis_info", "Impossible de récupérer les informations QGIS")


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