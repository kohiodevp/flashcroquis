# urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import (
    ProjectSessionViewSet, LayerViewSet, ParcelleViewSet, GeneratedFileViewSet,
    ProcessingJobViewSet, QRCodeScanViewSet, MapRenderViewSet,
    health_check, ping, qgis_info
)

# Configuration Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="Flash Croquis API",
        default_version='v1',
        description="API QGIS pour la gestion de projets cartographiques et génération de documents",
        contact=openapi.Contact(email="contact@flashcroquis.com"),
        license=openapi.License(name="Licence propriétaire"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    url="https://jubilant-fiesta-q6775vvwq9jh4wvg-8000.app.github.dev", 
)

# Configuration du routeur REST
router = DefaultRouter()
router.register(r'sessions', ProjectSessionViewSet, basename='projectsession')
router.register(r'layers', LayerViewSet, basename='layer')
router.register(r'parcelles', ParcelleViewSet, basename='parcelle')
router.register(r'files', GeneratedFileViewSet, basename='generatedfile')
router.register(r'processing-jobs', ProcessingJobViewSet, basename='processingjob')
router.register(r'renders', MapRenderViewSet, basename='maprender')

urlpatterns = [
    # Documentation API
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # Routes REST principales
    path('api/v1/', include(router.urls)),
    
    # Endpoints système
    path('api/v1/health/', health_check, name='health-check'),
    path('api/v1/ping/', ping, name='ping'),
    path('api/v1/qgis-info/', qgis_info, name='qgis-info'),

    # Admin Django
    path('admin/', admin.site.urls),
]

# Patterns d'URL additionnels pour des cas d'usage spécifiques
app_name = 'flashcroquis'