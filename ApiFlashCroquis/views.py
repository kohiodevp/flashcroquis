# views.py
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import FileResponse, HttpResponse
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser
import os
import json
from datetime import datetime
from .models import ProjectSession, Layer, GeneratedFile
from .serializers import (
    ProjectSessionSerializer, LayerSerializer, GeneratedFileSerializer,
    RenderMapSerializer, AddLayerSerializer, FileUploadSerializer,
    GetLayerFeaturesSerializer, ParcelleDetailSerializer, GenerateCroquisSerializer
)
from typing import Dict, Any, Optional, List
import math

# Configuration du logger
logger = logging.getLogger(__name__)

# Gestionnaire QGIS
class QGISManager:
    def __init__(self):
        self._initialized = False
        self._initialization_attempted = False
        self.qgs_app = None
        self.classes = {}
        self.init_errors = []
        
    def initialize(self):
        if self._initialized:
            return True, None
            
        if self._initialization_attempted:
            return False, self.init_errors
            
        self._initialization_attempted = True
        try:
            # Configuration de l'environnement
            import os
            os.environ['QT_NO_CPU_FEATURE'] = 'sse4.1,sse4.2,avx,avx2'
            
            # Importation des classes QGIS
            from qgis.core import (
                QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
                QgsMapSettings, QgsMapRendererParallelJob, QgsRectangle,
                QgsProcessingFeedback, QgsProcessingContext, QgsPalLayerSettings,
                QgsTextFormat, QgsVectorLayerSimpleLabeling, QgsPrintLayout,
                QgsLayoutItemMap, QgsLayoutItemLegend, QgsLayerTreeModel,
                QgsLayerTreeLayer, QgsLayerTreeGroup, QgsSingleSymbolRenderer,
                QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol, QgsGeometry,
                QgsFeature, QgsField, QgsVectorFileWriter, QgsWkbTypes
            )
            from PyQt5.QtCore import QVariant, QSize, QBuffer, QByteArray, QIODevice
            from PyQt5.QtGui import QImage, QPainter, QPen, QBrush, QFont, QColor
            
            # Initialisation de l'application QGIS
            self.qgs_app = QgsApplication([], False)
            self.qgs_app.initQgis()
            
            # Stockage des classes
            self.classes = {
                'QgsApplication': QgsApplication,
                'QgsProject': QgsProject,
                'QgsVectorLayer': QgsVectorLayer,
                'QgsRasterLayer': QgsRasterLayer,
                'QgsMapSettings': QgsMapSettings,
                'QgsMapRendererParallelJob': QgsMapRendererParallelJob,
                'QgsRectangle': QgsRectangle,
                'QgsProcessingFeedback': QgsProcessingFeedback,
                'QgsProcessingContext': QgsProcessingContext,
                'QgsPalLayerSettings': QgsPalLayerSettings,
                'QgsTextFormat': QgsTextFormat,
                'QgsVectorLayerSimpleLabeling': QgsVectorLayerSimpleLabeling,
                'QgsPrintLayout': QgsPrintLayout,
                'QgsLayoutItemMap': QgsLayoutItemMap,
                'QgsLayoutItemLegend': QgsLayoutItemLegend,
                'QgsLayerTreeModel': QgsLayerTreeModel,
                'QgsLayerTreeLayer': QgsLayerTreeLayer,
                'QgsLayerTreeGroup': QgsLayerTreeGroup,
                'QgsSingleSymbolRenderer': QgsSingleSymbolRenderer,
                'QgsFillSymbol': QgsFillSymbol,
                'QgsLineSymbol': QgsLineSymbol,
                'QgsMarkerSymbol': QgsMarkerSymbol,
                'QgsGeometry': QgsGeometry,
                'QgsFeature': QgsFeature,
                'QgsField': QgsField,
                'QgsVectorFileWriter': QgsVectorFileWriter,
                'QgsWkbTypes': QgsWkbTypes,
                'QVariant': QVariant,
                'QSize': QSize,
                'QBuffer': QBuffer,
                'QByteArray': QByteArray,
                'QIODevice': QIODevice,
                'QImage': QImage,
                'QPainter': QPainter,
                'QPen': QPen,
                'QBrush': QBrush,
                'QFont': QFont,
                'QColor': QColor
            }
            
            self._initialized = True
            logger.info("Environnement QGIS configuré")
            return True, None
            
        except Exception as e:
            error_msg = f"Erreur d'initialisation QGIS: {str(e)}"
            self.init_errors.append(error_msg)
            logger.error(error_msg)
            return False, self.init_errors
    
    def is_initialized(self):
        return self._initialized
        
    def get_classes(self):
        if not self._initialized:
            raise Exception("QGIS not initialized")
        return self.classes
        
    def get_errors(self):
        return self.init_errors

# Singleton pour le gestionnaire QGIS
def get_qgis_manager():
    if not hasattr(get_qgis_manager, 'instance'):
        get_qgis_manager.instance = QGISManager()
    return get_qgis_manager.instance

def initialize_qgis_if_needed():
    manager = get_qgis_manager()
    if not manager.is_initialized():
        return manager.initialize()
    return True, None

# Gestion des sessions de projet
project_sessions = {}
project_sessions_lock = None  # À implémenter avec threading.Lock() si nécessaire

class ProjectSessionManager:
    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.project = None
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.temporary_files = []
        
    def get_project(self, QgsProjectClass):
        if self.project is None:
            self.project = QgsProjectClass.instance()
        return self.project

def get_project_session(session_id=None):
    """Obtenir ou créer une session de projet"""
    global project_sessions
    if project_sessions_lock:
        with project_sessions_lock:
            if session_id and session_id in project_sessions:
                session = project_sessions[session_id]
            else:
                session = ProjectSessionManager(session_id)
                if not session_id:
                    session_id = session.session_id
                project_sessions[session_id] = session
            return session, session_id
    else:
        if session_id and session_id in project_sessions:
            session = project_sessions[session_id]
        else:
            session = ProjectSessionManager(session_id)
            if not session_id:
                session_id = session.session_id
            project_sessions[session_id] = session
        return session, session_id

# Fonctions utilitaires
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

def handle_exception(e, operation, default_message):
    """Gestion centralisée des exceptions"""
    logger.error(f"Erreur dans {operation}: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    return standard_response(
        success=False,
        error=str(e),
        message=default_message,
        status_code=500
    )

def format_layer_info(layer):
    """Formater les informations d'une couche"""
    try:
        extent = layer.extent() if hasattr(layer, 'extent') else None
        extent_info = {
            "xmin": extent.xMinimum() if extent else None,
            "xmax": extent.xMaximum() if extent else None,
            "ymin": extent.yMinimum() if extent else None,
            "ymax": extent.yMaximum() if extent else None
        } if extent else None
        
        return {
            "id": layer.id(),
            "name": layer.name(),
            "type": layer.typeName() if hasattr(layer, 'typeName') else "unknown",
            "source": layer.source() if hasattr(layer, 'source') else None,
            "extent": extent_info
        }
    except Exception as e:
        logger.warning(f"Erreur lors du formatage des informations de la couche: {e}")
        return {
            "id": getattr(layer, 'id', lambda: 'unknown')(),
            "name": getattr(layer, 'name', lambda: 'unknown')(),
            "type": "error",
            "error": str(e)
        }

def create_administrative_document_layout(
    project,
    session_id: str,
    config_data: Dict[str, Any],
    template_path: Optional[str] = None
) -> Optional['QgsPrintLayout']:
    """
    Crée un QgsPrintLayout pour un document administratif (croquis, rapport, etc.)
    basé sur un projet QGIS et une configuration.

    Args:
        project: L'instance QgsProject.
        session_id (str): L'ID de la session.
        config_data (dict): Configuration du document.
            Exemple de structure:
            {
                "document": {
                    "title": "Titre du Document",
                    "page_size": "A4",
                    "orientation": "Portrait", # ou "Landscape"
                    "margin_top": 10, # mm
                    "margin_bottom": 10,
                    "margin_left": 10,
                    "margin_right": 10
                },
                "maps": [
                    {
                        "id": "map1",
                        "x": 10, "y": 10, "width": 150, "height": 100, # mm
                        "layers": ["layer_id_1", "layer_id_2"], # Optionnel, sinon toutes
                        "extent": {"xmin": 0, "ymin": 0, "xmax": 100, "ymax": 100}, # Optionnel
                        "scale": 5000, # Optionnel
                        "grid": {
                            "enabled": true,
                            "interval": 100,
                            "color": "#888888",
                            "labels": true,
                            "label_position": "all" # all, edges, corners
                        },
                        "north_arrow": {
                            "enabled": true,
                            "x": 140, "y": 90, "size": 15 # mm
                        }
                    }
                ],
                "legends": [
                    {
                        "id": "legend1",
                        "title": "Légende",
                        "x": 170, "y": 10, "width": 30, "height": 80, # mm
                        "layers": ["layer_id_1"] # Optionnel, sinon toutes les couches de la carte liée
                    }
                ],
                "scales": [
                    {
                        "id": "scale1",
                        "x": 10, "y": 115, "width": 50, "height": 10, # mm
                        "map_id": "map1", # ID de la carte à laquelle l'échelle est liée
                        "style": "Numeric" # ou "Double" ou "Line Ticks Up"
                    }
                ],
                "labels": [
                    {
                        "id": "title_label",
                        "text": "Titre du Croquis",
                        "x": 100, "y": 5, "width": 100, "height": 10, # mm
                        "font": {"family": "Arial", "size": 14, "bold": true},
                        "alignment": "Center" # Left, Center, Right
                    },
                    {
                        "id": "date_label",
                        "text": "Généré le: [DATE]", # Placeholder
                        "x": 10, "y": 120, "width": 50, "height": 5,
                        "font": {"family": "Arial", "size": 8}
                    }
                ],
                "tables": [
                    {
                        "id": "table1",
                        "layer_id": "layer_id_1",
                        "x": 10, "y": 130, "width": 190, "height": 50, # mm
                        "columns": ["id", "nom", "surface"], # Colonnes à afficher
                        "max_features": 50 # Limite le nombre de lignes
                    }
                ],
                "images": [
                    {
                        "id": "logo",
                        "path": "/path/to/logo.png", # Chemin absolu ou relatif
                        "x": 10, "y": 5, "width": 20, "height": 10 # mm
                    }
                ]
            }
        template_path (str, optional): Chemin vers un fichier de template .qpt.

    Returns:
        QgsPrintLayout: Le layout créé, ou None en cas d'erreur.
    """
    try:
        manager = get_qgis_manager() # type: ignore
        classes = manager.get_classes()
        QgsPrintLayout = classes['QgsPrintLayout']
        QgsLayoutItemMap = classes['QgsLayoutItemMap']
        QgsLayoutItemLegend = classes['QgsLayoutItemLegend']
        QgsLayoutItemLabel = classes['QgsLayoutItemLabel']
        QgsLayoutItemScaleBar = classes['QgsLayoutItemScaleBar']
        QgsLayoutItemPicture = classes['QgsLayoutItemPicture']
        QgsLayoutItemPage = classes['QgsLayoutItemPage']
        QgsLayoutTable = classes['QgsLayoutTable']
        QgsLayoutItemAttributeTable = classes['QgsLayoutItemAttributeTable']
        QgsUnitTypes = classes['QgsUnitTypes']
        QgsLayoutPoint = classes['QgsLayoutPoint']
        QgsLayoutSize = classes['QgsLayoutSize']
        QgsRectangle = classes['QgsRectangle']
        QgsLayerTreeModel = classes['QgsLayerTreeModel']
        QgsLayerTreeLayer = classes['QgsLayerTreeLayer']
        QgsLayerTreeGroup = classes['QgsLayerTreeGroup']
        QFont = classes['QFont']
        QColor = classes['QColor']
        QgsLayoutFrame = classes['QgsLayoutFrame']

        # --- 1. Initialisation du Layout ---
        layout = QgsPrintLayout(project)
        
        if template_path and os.path.exists(template_path):
            # Charger à partir d'un template
            with open(template_path, 'r') as template_file:
                template_content = template_file.read()
            doc = QDomDocument()
            doc.setContent(template_content)
            layout.loadFromTemplate(doc, project)
            logger.info(f"Layout chargé depuis le template: {template_path}")
        else:
            # Initialisation par défaut
            layout.initializeDefaults()
            logger.info("Layout initialisé avec les paramètres par défaut")

        # --- 2. Configuration de la Page ---
        document_config = config_data.get("document", {})
        page_size = document_config.get("page_size", "A4")
        orientation_str = document_config.get("orientation", "Portrait")
        orientation = QgsLayoutItemPage.Portrait if orientation_str.lower() == "portrait" else QgsLayoutItemPage.Landscape

        page_collection = layout.pageCollection()
        if page_collection.pageCount() > 0:
            page = page_collection.page(0)
            page.setPageSize(page_size, orientation)
            # Note: Les marges du layout sont généralement gérées par le placement des éléments.

        # --- 3. Création d'un dictionnaire des éléments pour référencement croisé ---
        layout_items = {} # {"map1": QgsLayoutItemMap, ...}

        # --- 4. Ajout des Cartes (Maps) ---
        maps_config = config_data.get("maps", [])
        for map_conf in maps_config:
            try:
                map_id = map_conf["id"]
                x, y = map_conf["x"], map_conf["y"]
                width, height = map_conf["width"], map_conf["height"]

                map_item = QgsLayoutItemMap(layout)
                map_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
                map_item.attemptResize(QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters))

                # --- Configuration de la Carte ---
                # a. Couches visibles
                layer_ids_to_show = map_conf.get("layers")
                if layer_ids_to_show:
                    layers_to_show = [project.mapLayer(lid) for lid in layer_ids_to_show if project.mapLayer(lid)]
                    map_item.setLayers(layers_to_show)
                # Sinon, il utilise les couches par défaut du projet

                # b. Étendue
                extent_config = map_conf.get("extent")
                if extent_config:
                    extent_rect = QgsRectangle(
                        extent_config["xmin"], extent_config["ymin"],
                        extent_config["xmax"], extent_config["ymax"]
                    )
                    map_item.setExtent(extent_rect)
                # Si aucune étendue fournie, l'étendue par défaut du projet/couches sera utilisée

                # c. Échelle
                scale = map_conf.get("scale")
                if scale:
                    map_item.setScale(scale)

                # d. Grille
                grid_config = map_conf.get("grid", {})
                if grid_config.get("enabled", False):
                    grid = map_item.grid()
                    grid.setEnabled(True)
                    interval = grid_config.get("interval", 100)
                    grid.setIntervalX(interval)
                    grid.setIntervalY(interval)
                    
                    grid_color_hex = grid_config.get("color", "#888888")
                    grid_color = QColor(grid_color_hex)
                    if grid_color.isValid():
                        grid.setGridLineColor(grid_color)

                    if grid_config.get("labels", False):
                        grid.setAnnotationEnabled(True)
                        # Position des labels (simplifié)
                        label_pos = grid_config.get("label_position", "all")
                        # QGIS a des options plus complexes, ici un mapping basique
                        # ...

                # e. Flèche du Nord
                north_arrow_config = map_conf.get("north_arrow", {})
                if north_arrow_config.get("enabled", False):
                    # La flèche du nord est souvent ajoutée séparément comme une image
                    # On la stocke dans le config pour l'ajouter plus tard si besoin
                    pass # Géré dans une passe séparée ou par l'utilisateur

                layout.addLayoutItem(map_item)
                layout_items[map_id] = map_item
                logger.debug(f"Carte '{map_id}' ajoutée au layout.")

            except Exception as e:
                logger.error(f"Erreur lors de l'ajout de la carte {map_conf.get('id', 'unknown')}: {e}")

        # --- 5. Ajout des Légendes ---
        legends_config = config_data.get("legends", [])
        for legend_conf in legends_config:
            try:
                legend_id = legend_conf["id"]
                x, y = legend_conf["x"], legend_conf["y"]
                width, height = legend_conf["width"], legend_conf["height"]
                title = legend_conf.get("title", "Légende")
                linked_map_id = legend_conf.get("map_id") # Lier à une carte spécifique

                legend_item = QgsLayoutItemLegend(layout)
                legend_item.setTitle(title)
                legend_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
                # La taille est souvent gérée automatiquement ou par le frame
                
                # Lier à une carte si spécifiée
                if linked_map_id and linked_map_id in layout_items:
                    linked_map = layout_items[linked_map_id]
                    legend_item.setMap(linked_map)

                # Gérer les couches spécifiques pour la légende
                layer_ids_for_legend = legend_conf.get("layers")
                if layer_ids_for_legend:
                     # Créer un modèle d'arbre de couches personnalisé
                    root_group = QgsLayerTreeGroup() # Groupe temporaire
                    for lid in layer_ids_for_legend:
                        layer = project.mapLayer(lid)
                        if layer:
                            root_group.addLayer(layer)
                    legend_item.model().setRootGroup(root_group)
                    # Important: conserver la référence pour éviter le garbage collection
                    legend_item.custom_group = root_group

                layout.addLayoutItem(legend_item)
                layout_items[legend_id] = legend_item
                logger.debug(f"Légende '{legend_id}' ajoutée au layout.")

            except Exception as e:
                logger.error(f"Erreur lors de l'ajout de la légende {legend_conf.get('id', 'unknown')}: {e}")

        # --- 6. Ajout des Échelles (Scale Bars) ---
        scales_config = config_data.get("scales", [])
        for scale_conf in scales_config:
            try:
                scale_id = scale_conf["id"]
                x, y = scale_conf["x"], scale_conf["y"]
                width, height = scale_conf["width"], scale_conf["height"]
                linked_map_id = scale_conf.get("map_id")
                style = scale_conf.get("style", "Numeric") # Par défaut

                if not linked_map_id or linked_map_id not in layout_items:
                    logger.warning(f"Échelle '{scale_id}' ignorée: carte liée '{linked_map_id}' introuvable.")
                    continue

                linked_map = layout_items[linked_map_id]
                
                scalebar_item = QgsLayoutItemScaleBar(layout)
                scalebar_item.setLinkedMap(linked_map)
                scalebar_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
                # La largeur/hauteur est souvent gérée par le style
                
                # Appliquer le style (simplifié)
                if style.lower() == "numeric":
                    scalebar_item.setStyle('Numeric')
                elif style.lower() == "double":
                    scalebar_item.setStyle('Double Box')
                elif style.lower() == "line ticks up":
                    scalebar_item.setStyle('Line Ticks Up')
                # Ajouter d'autres styles si nécessaire

                layout.addLayoutItem(scalebar_item)
                layout_items[scale_id] = scalebar_item
                logger.debug(f"Échelle '{scale_id}' ajoutée au layout.")

            except Exception as e:
                logger.error(f"Erreur lors de l'ajout de l'échelle {scale_conf.get('id', 'unknown')}: {e}")

        # --- 7. Ajout des Étiquettes (Labels) ---
        labels_config = config_data.get("labels", [])
        for label_conf in labels_config:
            try:
                label_id = label_conf["id"]
                x, y = label_conf["x"], label_conf["y"]
                width, height = label_conf["width"], label_conf["height"]
                text = label_conf.get("text", "")
                font_config = label_conf.get("font", {})
                alignment = label_conf.get("alignment", "Left")

                # Remplacement de placeholders
                if "[DATE]" in text:
                    text = text.replace("[DATE]", datetime.now().strftime("%d/%m/%Y"))
                if "[SESSION_ID]" in text:
                    text = text.replace("[SESSION_ID]", session_id)
                # Ajouter d'autres placeholders si nécessaire

                label_item = QgsLayoutItemLabel(layout)
                label_item.setText(text)
                label_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
                label_item.attemptResize(QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters))

                # Configuration de la police
                font_family = font_config.get("family", "Arial")
                font_size = font_config.get("size", 10)
                font_bold = font_config.get("bold", False)
                font_italic = font_config.get("italic", False)
                
                font = QFont(font_family, font_size)
                font.setBold(font_bold)
                font.setItalic(font_italic)
                label_item.setFont(font)

                # Alignement (simplifié)
                if alignment.lower() == "center":
                    label_item.setHAlign(QgsLayoutItemLabel.AlignHCenter)
                elif alignment.lower() == "right":
                    label_item.setHAlign(QgsLayoutItemLabel.AlignRight)
                else: # Default/Left
                    label_item.setHAlign(QgsLayoutItemLabel.AlignLeft)

                layout.addLayoutItem(label_item)
                layout_items[label_id] = label_item
                logger.debug(f"Étiquette '{label_id}' ajoutée au layout.")

            except Exception as e:
                logger.error(f"Erreur lors de l'ajout de l'étiquette {label_conf.get('id', 'unknown')}: {e}")

        # --- 8. Ajout des Tables Attributaires ---
        tables_config = config_data.get("tables", [])
        for table_conf in tables_config:
            try:
                table_id = table_conf["id"]
                x, y = table_conf["x"], table_conf["y"]
                width, height = table_conf["width"], table_conf["height"]
                layer_id = table_conf.get("layer_id")
                columns = table_conf.get("columns", [])
                max_features = table_conf.get("max_features", 100)

                layer = project.mapLayer(layer_id) if layer_id else None
                if not layer or not layer.isValid():
                    logger.warning(f"Table '{table_id}' ignorée: couche '{layer_id}' invalide.")
                    continue

                # Création de la table
                table_item = QgsLayoutItemAttributeTable.create(layout)
                table_item.setVectorLayer(layer)
                
                # Configuration des colonnes
                if columns:
                    # QgsLayoutItemAttributeTable gère les champs via QgsAttributeTableConfig
                    # Cela peut être complexe, voici une approche basique
                    table_item.setDisplayedFields(columns)
                
                # Limiter le nombre de features
                table_item.setFeatureLimit(max_features)
                table_item.setDisplayOnlyVisibleFeatures(False) # Afficher tous les features de la couche
                
                # Positionnement et taille
                table_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
                table_item.attemptResize(QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters))

                layout.addLayoutItem(table_item)
                layout_items[table_id] = table_item
                logger.debug(f"Table '{table_id}' ajoutée au layout.")

            except Exception as e:
                logger.error(f"Erreur lors de l'ajout de la table {table_conf.get('id', 'unknown')}: {e}")

        # --- 9. Ajout d'Images (e.g., Logo) ---
        images_config = config_data.get("images", [])
        for img_conf in images_config:
            try:
                img_id = img_conf["id"]
                x, y = img_conf["x"], img_conf["y"]
                width, height = img_conf["width"], img_conf["height"]
                image_path = img_conf.get("path")

                if not image_path or not os.path.exists(image_path):
                    logger.warning(f"Image '{img_id}' ignorée: chemin invalide '{image_path}'.")
                    continue

                picture_item = QgsLayoutItemPicture(layout)
                picture_item.setPicturePath(image_path)
                picture_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
                picture_item.attemptResize(QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters))

                layout.addLayoutItem(picture_item)
                layout_items[img_id] = picture_item
                logger.debug(f"Image '{img_id}' ajoutée au layout.")

            except Exception as e:
                logger.error(f"Erreur lors de l'ajout de l'image {img_conf.get('id', 'unknown')}: {e}")

        # --- 10. Ajout de Flèches du Nord (comme éléments Picture) ---
        # Parcourir à nouveau les cartes pour ajouter les flèches du nord si configurées
        for map_conf in maps_config:
            north_arrow_config = map_conf.get("north_arrow", {})
            if north_arrow_config.get("enabled", False):
                try:
                    # Coordonnées de la flèche (relatives à la carte ou absolues)
                    # Ici, on utilise des coordonnées absolues comme dans la config
                    x = north_arrow_config.get("x", map_conf["x"] + map_conf["width"] - 20) # Défaut: coin haut droit
                    y = north_arrow_config.get("y", map_conf["y"] + 5)
                    size = north_arrow_config.get("size", 15)
                    
                    # Chemin vers l'icône de la flèche du nord
                    # QGIS fournit des SVG par défaut, mais on peut utiliser un chemin personnalisé
                    # Exemple avec un chemin par défaut (à adapter selon votre installation)
                    default_north_arrow_path = os.path.join(
                        os.environ.get('QGIS_PREFIX_PATH', '/usr'), 
                        'share/qgis/svg/arrows/NorthArrow_02.svg'
                    )
                    arrow_path = north_arrow_config.get("path", default_north_arrow_path)
                    
                    if not os.path.exists(arrow_path):
                         # Fallback: créer un triangle simple? Ou ignorer?
                         logger.warning(f"Chemin de flèche du nord non trouvé: {arrow_path}. Ignorée.")
                         continue

                    north_arrow_item = QgsLayoutItemPicture(layout)
                    north_arrow_item.setPicturePath(arrow_path)
                    north_arrow_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
                    north_arrow_item.attemptResize(QgsLayoutSize(size, size, QgsUnitTypes.LayoutMillimeters))
                    
                    # Optionnel: rotation, frame, etc.

                    layout.addLayoutItem(north_arrow_item)
                    # Pas besoin de le stocker dans layout_items si c'est purement décoratif
                    logger.debug(f"Flèche du nord ajoutée pour la carte {map_conf['id']}.")

                except Exception as e:
                    logger.error(f"Erreur lors de l'ajout de la flèche du nord pour la carte {map_conf.get('id', 'unknown')}: {e}")

        # --- 11. Rafraîchissement final ---
        # Il peut être utile de rafraîchir certains éléments
        for item in layout_items.values():
            if hasattr(item, 'refresh'):
                item.refresh()

        logger.info("Layout du document administratif créé avec succès.")
        return layout

    except Exception as e:
        logger.error(f"Erreur lors de la création du layout: {e}", exc_info=True)
        # handle_exception(e, "create_administrative_document_layout", "Impossible de créer le layout du document")
        return None

def export_layout(
    layout: 'QgsPrintLayout', 
    output_path: str, 
    format: str = 'PDF'
) -> bool:
    """
    Exporte un QgsPrintLayout vers un fichier.

    Args:
        layout (QgsPrintLayout): Le layout à exporter.
        output_path (str): Le chemin du fichier de sortie.
        format (str): Le format ('PDF', 'PNG', 'JPG').

    Returns:
        bool: True si l'exportation a réussi, False sinon.
    """
    try:
        manager = get_qgis_manager() # type: ignore
        classes = manager.get_classes()
        QgsLayoutExporter = classes['QgsLayoutExporter']

        exporter = QgsLayoutExporter(layout)
        
        if format.upper() == 'PDF':
            result = exporter.exportToPdf(output_path, QgsLayoutExporter.PdfExportSettings())
            return result == QgsLayoutExporter.Success
        elif format.upper() in ['PNG', 'JPG', 'JPEG']:
            settings = QgsLayoutExporter.ImageExportSettings()
            # Vous pouvez configurer la résolution, etc. ici
            # settings.dpi = 300
            if format.upper() == 'JPG' or format.upper() == 'JPEG':
                # QGIS exporte en PNG par défaut, la conversion JPG peut nécessiter un traitement supplémentaire
                # ou utiliser les paramètres de l'exporter si supporté.
                pass 
            result = exporter.exportToImage(output_path, settings)
            return result == QgsLayoutExporter.Success
        else:
            logger.error(f"Format d'exportation non supporté: {format}")
            return False
            
    except Exception as e:
        logger.error(f"Erreur lors de l'exportation du layout: {e}", exc_info=True)
        return False

class ProjectSessionViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les sessions de projet"""
    queryset = ProjectSession.objects.all()
    serializer_class = ProjectSessionSerializer
    lookup_field = 'session_id'
    
    @action(detail=False, methods=['post'], url_path='create')
    def create_project(self, request):
        """Créer un nouveau projet QGIS avec session persistante"""
        serializer = ProjectSessionSerializer(data=request.data)
        if serializer.is_valid():
            session = serializer.save()
            # Initialiser QGIS pour cette session
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            return Response({
                "success": True,
                "data": serializer.data,
                "message": "Projet créé avec succès"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success": False,
            "error": serializer.errors,
            "message": "Impossible de créer le projet"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='save')
    def save_project(self, request, session_id=None):
        """Sauvegarder le projet de la session courante"""
        try:
            session = self.get_object()
            project_path = request.data.get('project_path')
            
            # Logique de sauvegarde QGIS
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            manager = get_qgis_manager()
            classes = manager.get_classes()
            QgsProject = classes['QgsProject']
            
            # Obtenir la session QGIS
            qgis_session, _ = get_project_session(str(session.session_id))
            project = qgis_session.get_project(QgsProject)
            
            # Sauvegarder le projet
            if project_path:
                project.write(project_path)
            
            return standard_response(
                success=True,
                message="Projet sauvegardé avec succès"
            )
        except ProjectSession.DoesNotExist:
            return standard_response(
                success=False,
                error="Session not found",
                message="Session non trouvée",
                status_code=404
            )
        except Exception as e:
            return handle_exception(e, "save_project", "Impossible de sauvegarder le projet")
    
    @action(detail=True, methods=['get'], url_path='info')
    def project_info(self, request, session_id=None):
        """Obtenir les informations détaillées du projet courant de la session"""
        try:
            session = self.get_object()
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            # Obtenir les informations du projet
            manager = get_qgis_manager()
            classes = manager.get_classes()
            QgsProject = classes['QgsProject']
            
            # Obtenir la session QGIS
            qgis_session, _ = get_project_session(str(session.session_id))
            project = qgis_session.get_project(QgsProject)
            
            # Collecter les informations des couches
            layers_info = []
            for layer_id, layer in project.mapLayers().items():
                layers_info.append(format_layer_info(layer))
            
            project_info = {
                "session_id": str(session.session_id),
                "title": session.title,
                "crs": session.crs,
                "created_at": session.created_at.isoformat(),
                "layers_count": session.layers.count(),
                "project_file": project.fileName(),
                "layers": layers_info
            }
            
            return standard_response(
                success=True,
                data=project_info,
                message="Informations du projet récupérées avec succès"
            )
        except ProjectSession.DoesNotExist:
            return standard_response(
                success=False,
                error="Session not found",
                message="Session non trouvée",
                status_code=404
            )
        except Exception as e:
            return handle_exception(e, "project_info", "Impossible de récupérer les informations du projet")

class LayerViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les couches"""
    queryset = Layer.objects.all()
    serializer_class = LayerSerializer
    lookup_field = 'id'
    
    @action(detail=False, methods=['post'], url_path='add-vector')
    def add_vector_layer(self, request):
        """Ajouter une couche vectorielle au projet"""
        serializer = AddLayerSerializer(data=request.data)
        if serializer.is_valid():
            session_id = serializer.validated_data['session_id']
            data_source = serializer.validated_data['data_source']
            layer_name = serializer.validated_data.get('layer_name', '')
            
            try:
                session = ProjectSession.objects.get(session_id=session_id)
                success, error = initialize_qgis_if_needed()
                if not success:
                    return standard_response(
                        success=False,
                        error=error,
                        message="Échec de l'initialisation de QGIS",
                        status_code=500
                    )
                
                # Créer la couche vectorielle
                manager = get_qgis_manager()
                classes = manager.get_classes()
                QgsVectorLayer = classes['QgsVectorLayer']
                QgsProject = classes['QgsProject']
                
                # Obtenir la session QGIS
                qgis_session, _ = get_project_session(str(session_id))
                project = qgis_session.get_project(QgsProject)
                
                # Vérifier si le fichier existe
                if not os.path.exists(data_source) and not data_source.startswith(('http', 'https')):
                    return standard_response(
                        success=False,
                        error="data_source not found",
                        message=f"Fichier source non trouvé : {data_source}",
                        status_code=404
                    )
                
                layer = QgsVectorLayer(data_source, layer_name or 'Couche Vectorielle', 'ogr')
                
                if not layer.isValid():
                    return standard_response(
                        success=False,
                        error="Invalid layer",
                        message="Impossible de charger la couche vectorielle",
                        status_code=400
                    )
                
                # Ajouter la couche au projet
                project.addMapLayer(layer)
                
                # Enregistrer dans la base de données
                db_layer = Layer.objects.create(
                    session=session,
                    name=layer_name or layer.name(),
                    layer_type='vector',
                    data_source=data_source,
                    feature_count=layer.featureCount()
                )
                
                return standard_response(
                    success=True,
                    data=LayerSerializer(db_layer).data,
                    message="Couche vectorielle ajoutée avec succès"
                )
            except ProjectSession.DoesNotExist:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée",
                    status_code=404
                )
            except Exception as e:
                return handle_exception(e, "add_vector_layer", "Impossible d'ajouter la couche vectorielle")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='add-raster')
    def add_raster_layer(self, request):
        """Ajouter une couche raster au projet"""
        serializer = AddLayerSerializer(data=request.data)
        if serializer.is_valid():
            session_id = serializer.validated_data['session_id']
            data_source = serializer.validated_data['data_source']
            layer_name = serializer.validated_data.get('layer_name', '')
            
            try:
                session = ProjectSession.objects.get(session_id=session_id)
                success, error = initialize_qgis_if_needed()
                if not success:
                    return standard_response(
                        success=False,
                        error=error,
                        message="Échec de l'initialisation de QGIS",
                        status_code=500
                    )
                
                # Créer la couche raster
                manager = get_qgis_manager()
                classes = manager.get_classes()
                QgsRasterLayer = classes['QgsRasterLayer']
                QgsProject = classes['QgsProject']
                
                # Obtenir la session QGIS
                qgis_session, _ = get_project_session(str(session_id))
                project = qgis_session.get_project(QgsProject)
                
                # Vérifier si le fichier existe
                if not os.path.exists(data_source) and not data_source.startswith(('http', 'https')):
                    return standard_response(
                        success=False,
                        error="data_source not found",
                        message=f"Fichier source non trouvé : {data_source}",
                        status_code=404
                    )
                
                layer = QgsRasterLayer(data_source, layer_name or 'Couche Raster')
                
                if not layer.isValid():
                    return standard_response(
                        success=False,
                        error="Invalid layer",
                        message="Impossible de charger la couche raster",
                        status_code=400
                    )
                
                # Ajouter la couche au projet
                project.addMapLayer(layer)
                
                # Enregistrer dans la base de données
                db_layer = Layer.objects.create(
                    session=session,
                    name=layer_name or layer.name(),
                    layer_type='raster',
                    data_source=data_source
                )
                
                return standard_response(
                    success=True,
                    data=LayerSerializer(db_layer).data,
                    message="Couche raster ajoutée avec succès"
                )
            except ProjectSession.DoesNotExist:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée",
                    status_code=404
                )
            except Exception as e:
                return handle_exception(e, "add_raster_layer", "Impossible d'ajouter la couche raster")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='features')
    def get_layer_features(self, request, id=None):
        """Obtenir les caractéristiques d'une couche avec pagination"""
        serializer = GetLayerFeaturesSerializer(data={
            **request.GET.dict(),
            'layer_id': id
        })
        if serializer.is_valid():
            session_id = serializer.validated_data['session_id']
            layer_id = serializer.validated_data['layer_id']
            page = serializer.validated_data['page']
            limit = serializer.validated_data['limit']
            offset = serializer.validated_data['offset']
            
            try:
                session = ProjectSession.objects.get(session_id=session_id)
                layer = Layer.objects.get(id=layer_id, session=session)
                success, error = initialize_qgis_if_needed()
                if not success:
                    return standard_response(
                        success=False,
                        error=error,
                        message="Échec de l'initialisation de QGIS",
                        status_code=500
                    )
                
                # Obtenir la couche QGIS
                manager = get_qgis_manager()
                classes = manager.get_classes()
                QgsProject = classes['QgsProject']
                
                # Obtenir la session QGIS
                qgis_session, _ = get_project_session(str(session_id))
                project = qgis_session.get_project(QgsProject)
                
                # Obtenir la couche
                qgis_layer = project.mapLayer(str(layer_id))
                if not qgis_layer:
                    return standard_response(
                        success=False,
                        error="Layer not found",
                        message="Couche non trouvée",
                        status_code=404
                    )
                
                # Récupérer les features
                features_data = []
                feature_iterator = qgis_layer.getFeatures()
                feature_iterator.setLimit(limit)
                feature_iterator.setOffset(offset)
                
                for feature in feature_iterator:
                    # Récupérer les attributs
                    attrs = feature.attributes()
                    fields = feature.fields()
                    
                    # Convertir les attributs en dictionnaire
                    feature_data = {}
                    for i, attr in enumerate(attrs):
                        field_name = fields[i].name()
                        feature_data[field_name] = attr
                    
                    # Ajouter la géométrie si disponible
                    geometry = feature.geometry()
                    if geometry:
                        feature_data['geometry'] = {
                            'type': geometry.typeName(),
                            'wkt': geometry.asWkt()
                        }
                    
                    features_data.append(feature_data)
                
                total_features = qgis_layer.featureCount()
                
                result = {
                    'layer_id': str(layer_id),
                    'layer_name': layer.name,
                    'total_features': total_features,
                    'requested_features': len(features_data),
                    'offset': offset,
                    'limit': limit,
                    'has_more': offset + len(features_data) < total_features,
                    'features': features_data
                }
                
                return standard_response(
                    success=True,
                    data=result,
                    message=f"{len(features_data)} features récupérés sur {total_features} au total de la session '{session_id}'",
                    metadata={
                        'session_id': str(session_id),
                        'pagination': {
                            'current_page': page,
                            'total_pages': (total_features + limit - 1) // limit,
                            'per_page': limit,
                            'total_features': total_features
                        }
                    }
                )
            except (ProjectSession.DoesNotExist, Layer.DoesNotExist):
                return standard_response(
                    success=False,
                    error="Layer or session not found",
                    message="Couche ou session non trouvée",
                    status_code=404
                )
            except Exception as e:
                return handle_exception(e, "get_layer_features", "Impossible de récupérer les features de la couche")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='extent')
    def get_layer_extent(self, request, id=None):
        """Obtenir l'étendue géographique d'une couche"""
        session_id = request.GET.get('session_id')
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
            
        try:
            session = ProjectSession.objects.get(session_id=session_id)
            layer = Layer.objects.get(id=id, session=session)
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            # Obtenir l'étendue de la couche
            manager = get_qgis_manager()
            classes = manager.get_classes()
            QgsProject = classes['QgsProject']
            
            # Obtenir la session QGIS
            qgis_session, _ = get_project_session(str(session_id))
            project = qgis_session.get_project(QgsProject)
            
            # Obtenir la couche
            qgis_layer = project.mapLayer(str(id))
            if not qgis_layer:
                return standard_response(
                    success=False,
                    error="Layer not found",
                    message="Couche non trouvée",
                    status_code=404
                )
            
            extent = qgis_layer.extent()
            extent_data = {
                "xmin": extent.xMinimum(),
                "ymin": extent.yMinimum(),
                "xmax": extent.xMaximum(),
                "ymax": extent.yMaximum()
            }
            
            return standard_response(
                success=True,
                data=extent_data,
                message=f"Étendue de la couche '{layer.name}' de la session '{session_id}' récupérée",
                metadata={
                    'session_id': str(session_id),
                    'layer_id': str(id),
                    'layer_type': 'vector' if qgis_layer.type() == 0 else 'raster' if qgis_layer.type() == 1 else 'unknown',
                    'feature_count': qgis_layer.featureCount() if hasattr(qgis_layer, 'featureCount') else None
                }
            )
        except (ProjectSession.DoesNotExist, Layer.DoesNotExist):
            return standard_response(
                success=False,
                error="Layer or session not found",
                message="Couche ou session non trouvée",
                status_code=404
            )
        except Exception as e:
            return handle_exception(e, "get_layer_extent", "Impossible de récupérer l'étendue de la couche")
    
    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_layer(self, request, id=None):
        """Supprimer une couche du projet"""
        session_id = request.data.get('session_id')
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
            
        try:
            session = ProjectSession.objects.get(session_id=session_id)
            layer = Layer.objects.get(id=id, session=session)
            
            # Supprimer de QGIS
            success, error = initialize_qgis_if_needed()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            manager = get_qgis_manager()
            classes = manager.get_classes()
            QgsProject = classes['QgsProject']
            
            # Obtenir la session QGIS
            qgis_session, _ = get_project_session(str(session_id))
            project = qgis_session.get_project(QgsProject)
            
            # Supprimer la couche du projet
            project.removeMapLayer(str(id))
            
            # Supprimer de la base de données
            layer.delete()
            
            return standard_response(
                success=True,
                data={"layer_id": str(id), "session_id": str(session_id)},
                message="Couche supprimée avec succès"
            )
        except (ProjectSession.DoesNotExist, Layer.DoesNotExist):
            return standard_response(
                success=False,
                error="Layer or session not found",
                message="Couche ou session non trouvée",
                status_code=404
            )
        except Exception as e:
            return handle_exception(e, "remove_layer", "Impossible de supprimer la couche")

class MapViewSet(viewsets.ViewSet):
    """ViewSet pour les opérations de carte"""
    
    @action(detail=False, methods=['post'], url_path='render')
    def render_map(self, request):
        """Générer un rendu de carte avec options avancées"""
        serializer = RenderMapSerializer(data=request.data)
        if serializer.is_valid():
            session_id = serializer.validated_data['session_id']
            width = serializer.validated_data['width']
            height = serializer.validated_data['height']
            dpi = serializer.validated_data['dpi']
            format_image = serializer.validated_data['format_image']
            extent = serializer.validated_data.get('extent')
            background_color = serializer.validated_data['background_color']
            enable_grid = serializer.validated_data['enable_grid']
            grid_interval = serializer.validated_data['grid_interval']
            grid_color = serializer.validated_data['grid_color']
            grid_label_font_size = serializer.validated_data['grid_label_font_size']
            grid_horizontal_labels = serializer.validated_data['grid_horizontal_labels']
            grid_vertical_labels = serializer.validated_data['grid_vertical_labels']
            grid_label_position = serializer.validated_data['grid_label_position']
            show_points = serializer.validated_data.get('show_points')
            enable_point_labels = serializer.validated_data['enable_point_labels']
            label_field = serializer.validated_data['label_field']
            label_color = serializer.validated_data['label_color']
            label_size = serializer.validated_data['label_size']
            label_offset_x = serializer.validated_data['label_offset_x']
            label_offset_y = serializer.validated_data['label_offset_y']
            
            try:
                session = ProjectSession.objects.get(session_id=session_id)
                success, error = initialize_qgis_if_needed()
                if not success:
                    return standard_response(
                        success=False,
                        error=error,
                        message="Échec de l'initialisation de QGIS",
                        status_code=500
                    )
                
                # Créer les paramètres de carte
                manager = get_qgis_manager()
                classes = manager.get_classes()
                QgsProject = classes['QgsProject']
                QgsMapSettings = classes['QgsMapSettings']
                QgsMapRendererParallelJob = classes['QgsMapRendererParallelJob']
                QgsRectangle = classes['QgsRectangle']
                QSize = classes['QSize']
                QImage = classes['QImage']
                QPainter = classes['QPainter']
                QPen = classes['QPen']
                QBrush = classes['QBrush']
                QColor = classes['QColor']
                QFont = classes['QFont']
                
                # Obtenir la session QGIS
                qgis_session, _ = get_project_session(str(session_id))
                project = qgis_session.get_project(QgsProject)
                
                # Configuration du rendu
                map_settings = QgsMapSettings()
                map_settings.setOutputSize(QSize(width, height))
                map_settings.setOutputDpi(dpi)
                
                # Définir le CRS
                if project.crs().isValid():
                    map_settings.setDestinationCrs(project.crs())
                
                # Définir l'étendue si fournie
                if extent:
                    try:
                        coords = [float(x) for x in extent.split(',')]
                        if len(coords) == 4:
                            extent_rect = QgsRectangle(coords[0], coords[1], coords[2], coords[3])
                            map_settings.setExtent(extent_rect)
                    except ValueError:
                        pass  # Ignorer l'étendue invalide
                
                # Créer le job de rendu
                job = QgsMapRendererParallelJob(map_settings)
                job.start()
                
                # Attendre la fin du rendu
                while not job.finished():
                    pass
                
                # Obtenir l'image rendue
                image = job.renderedImage()
                
                # Convertir l'image en bytes
                from io import BytesIO
                buffer = BytesIO()
                if format_image.lower() == 'jpg':
                    image.save(buffer, "JPEG", quality=90)
                    content_type = 'image/jpeg'
                else:
                    image.save(buffer, "PNG")
                    content_type = 'image/png'
                
                # Créer la réponse HTTP
                response = HttpResponse(buffer.getvalue(), content_type=content_type)
                response['Content-Disposition'] = f'inline; filename="map_render.{format_image.lower()}"'
                return response
                
            except ProjectSession.DoesNotExist:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée",
                    status_code=404
                )
            except Exception as e:
                return handle_exception(e, "render_map", "Impossible de générer le rendu de la carte")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='parcelle-detail')
    def parcelle_detail(self, request):
        """Traiter une liste de points pour créer une parcelle"""
        serializer = ParcelleDetailSerializer(data=request.data)
        if serializer.is_valid():
            session_id = serializer.validated_data['session_id']
            points_data = serializer.validated_data['points']
            output_polygon_layer = serializer.validated_data.get('output_polygon_layer')
            output_points_layer = serializer.validated_data.get('output_points_layer')
            
            try:
                session = ProjectSession.objects.get(session_id=session_id)
                success, error = initialize_qgis_if_needed()
                if not success:
                    return standard_response(
                        success=False,
                        error=error,
                        message="Échec de l'initialisation de QGIS",
                        status_code=500
                    )
                
                # Parser les points
                try:
                    points = json.loads(points_data)
                except json.JSONDecodeError:
                    return standard_response(
                        success=False,
                        error="Invalid points format",
                        message="Le format des points doit être un JSON valide",
                        status_code=400
                    )
                
                # Traiter la parcelle avec QGIS
                manager = get_qgis_manager()
                classes = manager.get_classes()
                QgsProject = classes['QgsProject']
                QgsVectorLayer = classes['QgsVectorLayer']
                QgsGeometry = classes['QgsGeometry']
                QgsFeature = classes['QgsFeature']
                QgsField = classes['QgsField']
                QVariant = classes['QVariant']
                
                # Obtenir la session QGIS
                qgis_session, _ = get_project_session(str(session_id))
                project = qgis_session.get_project(QgsProject)
                
                # Créer le polygone
                if len(points) < 3:
                    return standard_response(
                        success=False,
                        error="Not enough points",
                        message="Il faut au moins 3 points pour créer un polygone",
                        status_code=400
                    )
                
                # Convertir les points
                qgis_points = []
                for point in points:
                    if isinstance(point, list) and len(point) == 2:
                        qgis_points.append(QgsPointXY(point[0], point[1]))
                    elif isinstance(point, dict) and 'x' in point and 'y' in point:
                        qgis_points.append(QgsPointXY(point['x'], point['y']))
                
                # Créer le polygone
                polygon_geom = QgsGeometry.fromPolygonXY([qgis_points])
                
                # Créer le layer polygone
                polygon_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Parcelle", "memory")
                polygon_provider = polygon_layer.dataProvider()
                
                # Ajouter les champs
                polygon_provider.addAttributes([
                    QgsField("id", QVariant.String),
                    QgsField("Superficie", QVariant.Double)
                ])
                polygon_layer.updateFields()
                
                # Créer la feature
                polygon_feature = QgsFeature()
                polygon_feature.setGeometry(polygon_geom)
                polygon_feature.setAttributes(["1", polygon_geom.area()])
                polygon_provider.addFeatures([polygon_feature])
                
                # Ajouter au projet
                project.addMapLayer(polygon_layer)
                
                # Calculer les résultats
                area_m2 = polygon_geom.area()
                points_count = len(qgis_points)
                
                return standard_response(
                    success=True,
                    data={
                        "area_m2": area_m2,
                        "points_count": points_count
                    },
                    message="Parcelle traitée avec succès"
                )
            except ProjectSession.DoesNotExist:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée",
                    status_code=404
                )
            except Exception as e:
                return handle_exception(e, "parcelle_detail", "Impossible de traiter la parcelle")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='generate-croquis')
    def generate_croquis(self, request):
        """Générer un croquis avec options avancées"""
        serializer = GenerateCroquisSerializer(data=request.data)
        if serializer.is_valid():
            session_id = serializer.validated_data['session_id']
            config_data = serializer.validated_data.get('config', {})
            template_id = serializer.validated_data.get('template_id', None)
            output_filename = serializer.validated_data['output_filename']
            format_croquis = serializer.validated_data['format_croquis']
            
            try:
                session_db = ProjectSession.objects.get(session_id=session_id)
                success, error = initialize_qgis_if_needed()
                if not success:
                    return standard_response(
                        success=False,
                        error=error,
                        message="Échec de l'initialisation de QGIS",
                        status_code=500
                    )
                
                # Générer le croquis avec QGIS
                manager = get_qgis_manager()
                classes = manager.get_classes()
                QgsProject = classes['QgsProject']
                QgsLayoutExporter = classes['QgsLayoutExporter'] 
                
                if project_sessions_lock:
                    with project_sessions_lock:
                        session_qgis = project_sessions.get(str(session_id))
                        if session_qgis is None:
                             return standard_response(
                                success=False,
                                error="QGIS Session not found",
                                message="Session QGIS non trouvée. Veuillez créer une nouvelle session.",
                                status_code=404
                            )
                else:
                     session_qgis = project_sessions.get(str(session_id))
                     if session_qgis is None:
                         return standard_response(
                            success=False,
                            error="QGIS Session not found",
                            message="Session QGIS non trouvée. Veuillez créer une nouvelle session.",
                            status_code=404
                        )

                project = session_qgis.get_project(QgsProject)
                
                template_path = None
                if template_id:
                    template = GeneratedFile.objects.get(id=template_id)
                    if template.file_path:
                        template_path = template.file_path
                
                layout = create_administrative_document_layout(project, str(session_id), config_data, template_path)
                if not layout:
                    return standard_response(
                        success=False,
                        error="Layout creation failed",
                        message="Impossible de créer le layout du document administratif.",
                        status_code=500
                    )
                
                full_output_path = os.path.join(settings.MEDIA_ROOT, output_filename)
                os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

                export_success = export_layout(layout, full_output_path, format=format_croquis)

                if not export_success:
                    return standard_response(
                        success=False,
                        error="Export failed",
                        message="Impossible d'exporter le croquis.",
                        status_code=500
                    )

                # Enregistrer le fichier généré
                generated_file_db = GeneratedFile.objects.create(
                    session=session_db, # Instance de ProjectSession
                    file_type='pdf', # Adapter si le format change
                    file_path=full_output_path, # Chemin absolu
                    metadata={'config': config_data, 'source': 'croquis'}
                )
                
                return standard_response(
                    success=True,
                    data={
                        "file_id": str(generated_file_db.id),
                        "file_url": generated_file_db.get_file_url(), # Utilise la méthode du modèle
                        "file_path": full_output_path, # Chemin absolu (optionnel)
                        "output_filename": output_filename,
                        "message": "Croquis généré avec succès"
                    },
                    message="Croquis généré et sauvegardé avec succès"
                )
            except ProjectSession.DoesNotExist:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée",
                    status_code=404
                )
            except Exception as e:
                return handle_exception(e, "generate_croquis", "Impossible de générer le croquis")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FileViewSet(viewsets.ViewSet):
    """ViewSet pour gérer les fichiers"""

    parser_classes = (MultiPartParser, FormParser)

    @action(detail=False, methods=['post'], url_path='upload', permission_classes=[AllowAny]) # Ou une permission plus stricte
    def upload_file(self, request):
        """
        Télécharger un fichier dans le répertoire MEDIA.
        """
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            uploaded_file = serializer.validated_data['file']
            session_id = serializer.validated_data.get('session_id')
            custom_name = serializer.validated_data.get('custom_name')
            file_type = serializer.validated_data.get('file_type', 'unknown')
            
            try:
                # 1. Déterminer le nom du fichier
                if custom_name:
                    # Nettoyer le nom personnalisé pour éviter les problèmes
                    filename = custom_name
                    if not os.path.splitext(filename)[1]:
                        # Ajouter l'extension d'origine si elle n'est pas présente
                        filename += os.path.splitext(uploaded_file.name)[1]
                else:
                    filename = uploaded_file.name

                # 2. Déterminer le chemin de destination
                # Vous pouvez organiser les fichiers par session, date, type, etc.
                if session_id:
                    # Exemple: media/uploads/<session_id>/<filename>
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(session_id))
                else:
                    # Exemple: media/uploads/<date>/<filename>
                    from datetime import datetime
                    today_str = datetime.now().strftime('%Y/%m/%d')
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', today_str)
                
                os.makedirs(upload_dir, exist_ok=True) # Crée les répertoires si nécessaire
                full_file_path = os.path.join(upload_dir, filename)
                
                # 3. Gérer les doublons de noms de fichiers
                base_name, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(full_file_path):
                    new_filename = f"{base_name}_{counter}{ext}"
                    full_file_path = os.path.join(upload_dir, new_filename)
                    counter += 1
                
                # 4. Sauvegarder le fichier
                with open(full_file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                # 5. (Optionnel) Enregistrer dans la base de données
                # Si vous voulez garder une trace dans GeneratedFile ou un nouveau modèle
                # Par exemple, en utilisant un modèle FileRecord ou en réutilisant GeneratedFile
                # generated_file_db = GeneratedFile.objects.create(
                #     session=ProjectSession.objects.get(session_id=session_id) if session_id else None,
                #     file_type=file_type.split('_')[0] if '_' in file_type else file_type, # Simplifier le type
                #     file_path=full_file_path,
                #     metadata={
                #         'original_name': uploaded_file.name,
                #         'size': uploaded_file.size,
                #         'content_type': uploaded_file.content_type
                #     }
                # )
                
                # 6. Préparer l'URL d'accès (si vous avez MEDIA_URL configuré)
                relative_path = os.path.relpath(full_file_path, settings.MEDIA_ROOT)
                file_url = os.path.join(settings.MEDIA_URL, relative_path).replace('\\', '/') # Pour Windows

                return standard_response(
                    success=True,
                    data={
                        'message': 'Fichier téléchargé avec succès',
                        'file_name': os.path.basename(full_file_path),
                        'file_path': full_file_path, # Chemin absolu sur le serveur
                        'file_url': file_url, # URL relative accessible via le web
                        'size': uploaded_file.size,
                        'content_type': uploaded_file.content_type,
                        # 'db_id': generated_file_db.id if 'generated_file_db' in locals() else None
                    },
                    message="Fichier téléchargé avec succès"
                )
            except ProjectSession.DoesNotExist:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session spécifiée non trouvée",
                    status_code=status.HTTP_400_BAD_REQUEST # 400 car l'ID était fourni mais invalide
                )
            except Exception as e:
                 return handle_exception(e, "upload_file", "Erreur lors du téléchargement du fichier")
        
        else:
            # Retourner les erreurs de validation du sérialiseur
            return standard_response(
                success=False,
                error=serializer.errors,
                message="Données de téléchargement invalides",
                status_code=status.HTTP_400_BAD_REQUEST
            )

    
    @action(detail=False, methods=['get'], url_path='list')
    def list_files(self, request):
        """Lister les fichiers dans le répertoire MEDIA"""
        directory = request.GET.get('directory', '')
        file_type = request.GET.get('type', 'all')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        try:
            # Lister les fichiers réels
            media_root = settings.MEDIA_ROOT
            target_directory = os.path.join(media_root, directory) if directory else media_root
            
            if not os.path.exists(target_directory):
                return standard_response(
                    success=False,
                    error="Directory not found",
                    message="Répertoire non trouvé",
                    status_code=404
                )
            
            all_files = []
            for filename in os.listdir(target_directory):
                file_path = os.path.join(target_directory, filename)
                if os.path.isfile(file_path):
                    stat_info = os.stat(file_path)
                    file_info = {
                        'name': filename,
                        'size': stat_info.st_size,
                        'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        'type': 'image' if filename.endswith(('.png', '.jpg', '.jpeg')) else
                                'document' if filename.endswith(('.pdf', '.doc', '.docx')) else
                                'other'
                    }
                    
                    # Filtrer par type si spécifié
                    if file_type != 'all' and file_info['type'] != file_type:
                        continue
                        
                    all_files.append(file_info)
            
            # Tri par date de modification (le plus récent en premier)
            all_files.sort(key=lambda x: x['modified'], reverse=True)
            
            # Pagination
            total_count = len(all_files)
            start_index = (page - 1) * per_page
            end_index = min(start_index + per_page, total_count)
            paginated_files = all_files[start_index:end_index]
            
            return standard_response(
                success=True,
                data={
                    'files': paginated_files,
                    'pagination': {
                        'current_page': page,
                        'total_pages': (total_count + per_page - 1) // per_page,
                        'per_page': per_page,
                        'total_count': total_count
                    }
                },
                message="Fichiers listés avec succès"
            )
        except Exception as e:
            return handle_exception(e, "list_files", "Impossible de lister les fichiers")
    
    @action(detail=True, methods=['get'], url_path='download')
    def download_file(self, request, pk=None):
        """Télécharger un fichier généré"""
        try:
            generated_file = GeneratedFile.objects.get(id=pk)
            
            # Vérifier si le fichier existe
            if os.path.exists(generated_file.file_path):
                response = FileResponse(
                    open(generated_file.file_path, 'rb'),
                    as_attachment=True,
                    filename=os.path.basename(generated_file.file_path)
                )
                return response
            else:
                return standard_response(
                    success=False,
                    error="File not found",
                    message="Fichier non trouvé",
                    status_code=404
                )
        except GeneratedFile.DoesNotExist:
            return standard_response(
                success=False,
                error="File not found",
                message="Fichier non trouvé",
                status_code=404
            )
        except Exception as e:
            return handle_exception(e, "download_file", "Impossible de télécharger le fichier")