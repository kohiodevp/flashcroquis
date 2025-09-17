# admin.py
from django.contrib import admin
from .models import ProjectSession, Layer, GeneratedFile

@admin.register(ProjectSession)
class ProjectSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'title', 'crs', 'created_at', 'last_accessed')
    list_filter = ('created_at', 'last_accessed', 'crs')
    search_fields = ('title', 'session_id')
    readonly_fields = ('session_id', 'created_at', 'last_accessed')
    ordering = ('-created_at',)

@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'name', 'layer_type', 'geometry_type', 'feature_count', 'created_at')
    list_filter = ('layer_type', 'geometry_type', 'created_at', 'session')
    search_fields = ('name', 'id', 'session__title', 'session__session_id')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)

@admin.register(GeneratedFile)
class GeneratedFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'file_type', 'file_path', 'created_at')
    list_filter = ('file_type', 'created_at', 'session')
    search_fields = ('file_path', 'id', 'session__title', 'session__session_id')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)

# Configuration de l'interface d'administration
admin.site.site_header = "Flash Croquis Administration"
admin.site.site_title = "Flash Croquis Admin"
admin.site.index_title = "Bienvenue dans l'administration Flash Croquis"