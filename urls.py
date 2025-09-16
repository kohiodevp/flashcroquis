# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import (
    ProjectSessionViewSet, LayerViewSet, ParcelleViewSet, GeneratedFileViewSet,
    ProcessingJobViewSet, QRCodeScanViewSet, MapRenderViewSet,
    generate_advanced_pdf, generate_croquis, qr_scanner,
    health_check, ping, qgis_info, list_files
)

# Configuration Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="FlashCroquis API",
        default_version='v1',
        description="API QGIS pour la gestion de projets cartographiques et génération de documents",
        contact=openapi.Contact(email="contact@flashcroquis.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# Configuration du routeur REST
router = DefaultRouter()
router.register(r'sessions', ProjectSessionViewSet, basename='projectsession')
router.register(r'layers', LayerViewSet, basename='layer')
router.register(r'parcelles', ParcelleViewSet, basename='parcelle')
router.register(r'files', GeneratedFileViewSet, basename='generatedfile')
router.register(r'processing-jobs', ProcessingJobViewSet, basename='processingjob')
router.register(r'qr-scans', QRCodeScanViewSet, basename='qrcodescan')
router.register(r'renders', MapRenderViewSet, basename='maprender')

urlpatterns = [
    # Documentation API
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # Routes REST principales
    path('api/v1/', include(router.urls)),
    
    # Endpoints spécialisés
    path('api/v1/generate-pdf/', generate_advanced_pdf, name='generate-advanced-pdf'),
    path('api/v1/generate-croquis/', generate_croquis, name='generate-croquis'),
    path('api/v1/qr-scanner/', qr_scanner, name='qr-scanner'),
    
    # Endpoints système
    path('api/v1/health/', health_check, name='health-check'),
    path('api/v1/ping/', ping, name='ping'),
    path('api/v1/qgis-info/', qgis_info, name='qgis-info'),
    path('api/v1/list-files/', list_files, name='list-files'),
    
    # Endpoints de compatibilité avec l'ancienne API
    # Sessions/Projets
    path('api/v1/create-project/', ProjectSessionViewSet.as_view({'post': 'create'}), name='create-project'),
    path('api/v1/load-project/', ProjectSessionViewSet.as_view({'post': 'load_project'}), name='load-project'),
    path('api/v1/save-project/', ProjectSessionViewSet.as_view({'post': 'save_project'}), name='save-project'),
    path('api/v1/project-info/', ProjectSessionViewSet.as_view({'get': 'retrieve'}), name='project-info'),
    
    # Couches
    path('api/v1/get-layers/', LayerViewSet.as_view({'get': 'list'}), name='get-layers'),
    path('api/v1/add-vector-layer/', LayerViewSet.as_view({'post': 'add_vector'}), name='add-vector-layer'),
    path('api/v1/add-raster-layer/', LayerViewSet.as_view({'post': 'add_raster'}), name='add-raster-layer'),
    path('api/v1/remove-layer/', LayerViewSet.as_view({'delete': 'remove_layer'}), name='remove-layer'),
    path('api/v1/zoom-to-layer/', LayerViewSet.as_view({'post': 'zoom_to'}), name='zoom-to-layer'),
    path('api/v1/get-layer-features/<uuid:layer_id>/', LayerViewSet.as_view({'get': 'features'}), name='get-layer-features'),
    path('api/v1/get-layer-extent/<uuid:layer_id>/', LayerViewSet.as_view({'get': 'extent'}), name='get-layer-extent'),
    
    # Processing
    path('api/v1/execute-processing/', ProcessingJobViewSet.as_view({'post': 'execute'}), name='execute-processing'),
    
    # Rendering
    path('api/v1/render-map/', MapRenderViewSet.as_view({'post': 'render'}), name='render-map'),
    
    # Parcelles (endpoints spécialisés)
    path('api/v1/parcelles-list/', ParcelleViewSet.as_view({'get': 'list', 'post': 'create'}), name='parcelles-list'),
    path('api/v1/parcelle-detail/<str:parcelle_id>/', ParcelleViewSet.as_view({'get': 'retrieve', 'post': 'update'}), name='parcelle-detail'),
    
    # Fichiers
    path('api/v1/download-file/<uuid:file_id>/', GeneratedFileViewSet.as_view({'get': 'download'}), name='download-file'),
]

# Patterns d'URL additionnels pour des cas d'usage spécifiques
app_name = 'flashcroquis'