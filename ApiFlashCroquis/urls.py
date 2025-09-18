# urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .views import ProjectSessionViewSet, LayerViewSet, MapViewSet, FileViewSet

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

router = DefaultRouter()
router.register(r'sessions', ProjectSessionViewSet, basename='session')
router.register(r'layers', LayerViewSet, basename='layer')
router.register(r'files', FileViewSet, basename='file') 

urlpatterns = [
    # Documentation API
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    path('api/', include(router.urls)),
    path('api/map/', include([
        path('render/', MapViewSet.as_view({'post': 'render_map'}), name='render-map'),
        path('parcelle-detail/', MapViewSet.as_view({'post': 'parcelle_detail'}), name='parcelle-detail'),
        path('generate-croquis/', MapViewSet.as_view({'post': 'generate_croquis'}), name='generate-croquis'),
    ])),
    # path('api/files/', include([
    #     path('list/', FileViewSet.as_view({'get': 'list_files'}), name='list-files'),
    #     path('<uuid:pk>/download/', FileViewSet.as_view({'get': 'download_file'}), name='download-file'),
    # ])),

    # Admin Django
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
