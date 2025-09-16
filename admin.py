# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    ProjectSession, Layer, Parcelle, PointSommet, GeneratedFile,
    ProcessingJob, QRCodeScan, LayerStyle, MapRender
)


@admin.register(ProjectSession)
class ProjectSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'status', 'user', 'layers_count', 'created_at', 'last_accessed']
    list_filter = ['status', 'created_at', 'last_accessed']
    search_fields = ['title', 'user__username']
    readonly_fields = ['id', 'created_at', 'last_accessed', 'layers_count', 'project_file_link']
    fieldsets = (
        ('Informations générales', {
            'fields': ('id', 'title', 'crs', 'status', 'user')
        }),
        ('Fichiers', {
            'fields': ('project_file', 'project_file_link')
        }),
        ('Métadonnées', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_accessed'),
            'classes': ('collapse',)
        }),
    )
    
    def layers_count(self, obj):
        return obj.layers.count()
    layers_count.short_description = 'Nb Couches'
    
    def project_file_link(self, obj):
        if obj.project_file:
            return format_html(
                '<a href="{}" target="_blank">Télécharger</a>',
                obj.project_file.url
            )
        return "Aucun fichier"
    project_file_link.short_description = 'Fichier Projet'


class LayerStyleInline(admin.StackedInline):
    model = LayerStyle
    max_num = 1
    extra = 0
    fieldsets = (
        ('Style des symboles', {
            'fields': ('symbol_color', 'symbol_size', 'symbol_style', 'line_width', 'fill_color', 'opacity')
        }),
        ('Labels', {
            'fields': ('show_labels', 'label_field', 'label_color', 'label_size', 'label_offset_x', 'label_offset_y'),
            'classes': ('collapse',)
        })
    )


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'layer_type', 'geometry_type', 'session', 'feature_count', 'is_visible', 'created_at']
    list_filter = ['layer_type', 'geometry_type', 'is_visible', 'created_at']
    search_fields = ['name', 'session__title']
    readonly_fields = ['id', 'qgis_layer_id', 'created_at', 'updated_at', 'extent_display']
    inlines = [LayerStyleInline]
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'session', 'layer_type', 'geometry_type', 'is_visible')
        }),
        ('Source', {
            'fields': ('source_file', 'source_url', 'crs')
        }),
        ('Données', {
            'fields': ('feature_count', 'extent', 'extent_display'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('id', 'qgis_layer_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def extent_display(self, obj):
        if obj.extent:
            return format_html(
                "<pre>{}</pre>",
                mark_safe(str(obj.extent).replace(',', ',\n'))
            )
        return "Non défini"
    extent_display.short_description = 'Étendue formatée'


class PointSommetInline(admin.TabularInline):
    model = PointSommet
    extra = 0
    readonly_fields = ['distance', 'created_at']
    ordering = ['ordre']


@admin.register(Parcelle)
class ParcelleAdmin(admin.ModelAdmin):
    list_display = ['id', 'nom', 'superficie', 'proprietaire', 'status', 'session', 'created_at']
    list_filter = ['status', 'created_at', 'session']
    search_fields = ['id', 'nom', 'proprietaire', 'localisation']
    readonly_fields = ['created_at', 'updated_at', 'geometry_display']
    inlines = [PointSommetInline]
    fieldsets = (
        ('Informations cadastrales', {
            'fields': ('id', 'nom', 'superficie', 'proprietaire', 'status')
        }),
        ('Localisation', {
            'fields': ('localisation', 'adresse')
        }),
        ('Données techniques', {
            'fields': ('session', 'layer', 'geometry', 'geometry_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def geometry_display(self, obj):
        if obj.geometry:
            return format_html(
                "<pre>{}</pre>",
                mark_safe(str(obj.geometry)[:500] + "..." if len(str(obj.geometry)) > 500 else str(obj.geometry))
            )
        return "Non défini"
    geometry_display.short_description = 'Géométrie'


@admin.register(GeneratedFile)
class GeneratedFileAdmin(admin.ModelAdmin):
    list_display = ['filename', 'file_type', 'session', 'size_display', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['filename', 'session__title']
    readonly_fields = ['id', 'size_bytes', 'created_at', 'file_link', 'config_display']
    fieldsets = (
        ('Fichier', {
            'fields': ('filename', 'file_type', 'file_path', 'file_link')
        }),
        ('Métadonnées', {
            'fields': ('session', 'size_bytes', 'generation_config', 'config_display')
        }),
        ('System', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def size_display(self, obj):
        size = obj.size_bytes
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    size_display.short_description = 'Taille'
    
    def file_link(self, obj):
        if obj.file_path:
            return format_html(
                '<a href="{}" target="_blank">Télécharger</a>',
                obj.file_path.url
            )
        return "Aucun fichier"
    file_link.short_description = 'Lien fichier'
    
    def config_display(self, obj):
        if obj.generation_config:
            return format_html(
                "<pre>{}</pre>",
                mark_safe(str(obj.generation_config)[:300] + "..." if len(str(obj.generation_config)) > 300 else str(obj.generation_config))
            )
        return "Aucune configuration"
    config_display.short_description = 'Configuration'


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    list_display = ['algorithm_name', 'status', 'session', 'duration_display', 'created_at']
    list_filter = ['status', 'algorithm_name', 'created_at']
    search_fields = ['algorithm_name', 'session__title']
    readonly_fields = ['id', 'duration_display', 'created_at', 'started_at', 'completed_at', 'parameters_display', 'result_display']
    fieldsets = (
        ('Job', {
            'fields': ('algorithm_name', 'status', 'session')
        }),
        ('Paramètres', {
            'fields': ('parameters', 'parameters_display'),
            'classes': ('collapse',)
        }),
        ('Résultats', {
            'fields': ('result', 'result_display', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration_display'),
            'classes': ('collapse',)
        })
    )
    
    def duration_display(self, obj):
        if obj.started_at and obj.completed_at:
            duration = (obj.completed_at - obj.started_at).total_seconds()
            return f"{duration:.2f}s"
        return "N/A"
    duration_display.short_description = 'Durée'
    
    def parameters_display(self, obj):
        if obj.parameters:
            return format_html(
                "<pre>{}</pre>",
                mark_safe(str(obj.parameters)[:300] + "..." if len(str(obj.parameters)) > 300 else str(obj.parameters))
            )
        return "Aucun paramètre"
    parameters_display.short_description = 'Paramètres formatés'
    
    def result_display(self, obj):
        if obj.result:
            return format_html(
                "<pre>{}</pre>",
                mark_safe(str(obj.result)[:300] + "..." if len(str(obj.result)) > 300 else str(obj.result))
            )
        return "Aucun résultat"
    result_display.short_description = 'Résultat formaté'


@admin.register(QRCodeScan)
class QRCodeScanAdmin(admin.ModelAdmin):
    list_display = ['data_type', 'validity', 'session', 'scanned_at', 'raw_data_preview']
    list_filter = ['data_type', 'validity', 'scanned_at']
    search_fields = ['raw_data', 'session__title']
    readonly_fields = ['id', 'scanned_at', 'processed_data_display']
    fieldsets = (
        ('Scan', {
            'fields': ('raw_data', 'data_type', 'validity', 'session')
        }),
        ('Données traitées', {
            'fields': ('processed_data', 'processed_data_display'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('id', 'scanned_at'),
            'classes': ('collapse',)
        })
    )
    
    def raw_data_preview(self, obj):
        preview = obj.raw_data[:50]
        if len(obj.raw_data) > 50:
            preview += "..."
        return preview
    raw_data_preview.short_description = 'Aperçu données'
    
    def processed_data_display(self, obj):
        if obj.processed_data:
            return format_html(
                "<pre>{}</pre>",
                mark_safe(str(obj.processed_data))
            )
        return "Aucune donnée traitée"
    processed_data_display.short_description = 'Données formatées'


@admin.register(MapRender)
class MapRenderAdmin(admin.ModelAdmin):
    list_display = ['session', 'format_output', 'dimensions', 'created_at']
    list_filter = ['format_output', 'show_grid', 'created_at']
    search_fields = ['session__title']
    readonly_fields = ['id', 'created_at', 'image_preview', 'config_display']
    fieldsets = (
        ('Paramètres de rendu', {
            'fields': ('session', 'width', 'height', 'dpi', 'format_output', 'quality')
        }),
        ('Style', {
            'fields': ('background_color', 'bbox', 'scale', 'show_grid'),
            'classes': ('collapse',)
        }),
        ('Configuration avancée', {
            'fields': ('grid_config', 'render_config', 'config_display'),
            'classes': ('collapse',)
        }),
        ('Résultat', {
            'fields': ('image_file', 'image_preview')
        }),
        ('Métadonnées', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def dimensions(self, obj):
        return f"{obj.width}x{obj.height}"
    dimensions.short_description = 'Dimensions'
    
    def image_preview(self, obj):
        if obj.image_file:
            return format_html(
                '<img src="{}" width="200" height="150" style="object-fit: cover;" />',
                obj.image_file.url
            )
        return "Aucune image"
    image_preview.short_description = 'Aperçu'
    
    def config_display(self, obj):
        config = {}
        if obj.grid_config:
            config['grid'] = obj.grid_config
        if obj.render_config:
            config['render'] = obj.render_config
        
        if config:
            return format_html(
                "<pre>{}</pre>",
                mark_safe(str(config)[:400] + "..." if len(str(config)) > 400 else str(config))
            )
        return "Aucune configuration"
    config_display.short_description = 'Configuration complète'


@admin.register(LayerStyle)
class LayerStyleAdmin(admin.ModelAdmin):
    list_display = ['layer', 'symbol_color', 'symbol_size', 'show_labels', 'updated_at']
    list_filter = ['show_labels', 'symbol_style', 'updated_at']
    search_fields = ['layer__name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Couche', {
            'fields': ('layer',)
        }),
        ('Style des symboles', {
            'fields': ('symbol_color', 'symbol_size', 'symbol_style', 'line_width', 'fill_color', 'opacity')
        }),
        ('Labels', {
            'fields': ('show_labels', 'label_field', 'label_color', 'label_size', 'label_offset_x', 'label_offset_y')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# Configuration de l'interface d'administration
admin.site.site_header = "FlashCroquis Administration"
admin.site.site_title = "FlashCroquis Admin"
admin.site.index_title = "Bienvenue dans l'administration FlashCroquis"