# qgis_utils.py
import io
import locale
import math
import os
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from threading import Lock
from django.conf import settings

# Gestion des sessions et QGIS
project_sessions = {}
project_sessions_lock = Lock()
qgis_manager = None

# Logger
logger = logging.getLogger(__name__)

# Classes QGIS (à importer au démarrage)
qgis_classes = {}
_A = True


def get_qgis_manager():
    """Obtenir le gestionnaire QGIS global"""
    global qgis_manager
    if qgis_manager is None:
        qgis_manager = QgisManager()
    return qgis_manager


def initialize_qgis_if_needed():
    """Initialiser QGIS si nécessaire"""
    manager = get_qgis_manager()
    if not manager.is_initialized():
        return manager.initialize()
    return True, None


def get_project_session(session_id=None):
    """Obtenir ou créer une session de projet"""
    with project_sessions_lock:
        if session_id and session_id in project_sessions:
            session = project_sessions[session_id]
        else:
            session = ProjectSessionManager(session_id)
            if not session_id:
                session_id = session.session_id
            project_sessions[session_id] = session
    return session, session_id


class QgisManager:
    """Gestionnaire QGIS centralisé"""
    
    def __init__(self):
        self._initialized = False
        self._initialization_attempted = False
        self.qgs_app = None
        self.classes = {}
        self.init_errors = []
    
    def initialize(self):
        """Initialiser QGIS avec gestion correcte de processing"""
        if self._initialized:
            return True, None
            
        if self._initialization_attempted:
            return False, "Initialization already attempted"
            
        self._initialization_attempted = True
        logger.info("=== DÉBUT DE L'INITIALISATION QGIS ===")
        
        try:
            # Configuration de l'environnement QGIS
            self._setup_qgis_environment()
            
            # Importation des modules QGIS
            from PyQt5.QtCore import QCoreApplication
            from qgis.core import (
                Qgis, QgsApplication, QgsProject, QgsVectorLayer,
                QgsRasterLayer, QgsMapSettings, QgsMapRendererParallelJob,
                QgsProcessingFeedback, QgsProcessingContext, QgsRectangle,
                QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling,
                QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLegend,
                QgsLayoutItemLabel, QgsLayoutExporter, QgsLayoutItemPicture,
                QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsLayoutItemPage,
                QgsLayoutItemScaleBar, QgsLayoutItemHtml,
                QgsCoordinateReferenceSystem, QgsRectangle,
                QgsMapLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsFields, QgsField,
                QgsVectorFileWriter, QgsVectorDataProvider, QgsWkbTypes, QgsLayerTreeLayer,
                QgsLinePatternFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSymbol, QgsSingleSymbolRenderer,
                QgsLayerTreeGroup, QgsLayerTreeModel, QgsLegendStyle, QgsExpression, QgsExpressionContext,
                QgsExpressionContextUtils, QgsTextBackgroundSettings, QgsLayoutItemShape, QgsLayoutItemMapGrid,
                QgsPoint
            )
            
            # Initialisation de l'application QGIS
            logger.info("Initialisation de l'application QGIS...")
            if not QgsApplication.instance():
                self.qgs_app = QgsApplication([], False)
                self.qgs_app.initQgis()
                logger.info("Application QGIS initialisée")
            else:
                self.qgs_app = QgsApplication.instance()
                logger.info("Instance QGIS existante utilisée")
            
            # Importation de processing
            try:
                import processing
                logger.info("Module processing importé avec succès")
            except ImportError:
                try:
                    from qgis import processing
                    logger.info("Module qgis.processing importé avec succès")
                except ImportError:
                    logger.warning("Module processing non disponible")
                    # Création d'un mock processing
                    class MockProcessing:
                        @staticmethod
                        def run(*args, **kwargs):
                            raise NotImplementedError("Processing module not available")
                    processing = MockProcessing()
            
            # Stockage des classes
            self.classes = {
                'Qgis': Qgis,
                'QgsApplication': QgsApplication,
                'QgsProject': QgsProject,
                'QgsVectorLayer': QgsVectorLayer,
                'QgsRasterLayer': QgsRasterLayer,
                'QgsMapSettings': QgsMapSettings,
                'QgsMapRendererParallelJob': QgsMapRendererParallelJob,
                'QgsProcessingFeedback': QgsProcessingFeedback,
                'QgsProcessingContext': QgsProcessingContext,
                'QgsRectangle': QgsRectangle,
                'processing': processing,
                'QgsPalLayerSettings': QgsPalLayerSettings,
                'QgsTextFormat': QgsTextFormat,
                'QgsVectorLayerSimpleLabeling': QgsVectorLayerSimpleLabeling,
                'QgsPrintLayout': QgsPrintLayout,
                'QgsLayoutItemMap': QgsLayoutItemMap,
                'QgsLayoutItemLegend': QgsLayoutItemLegend,
                'QgsLayoutItemLabel': QgsLayoutItemLabel,
                'QgsLayoutExporter': QgsLayoutExporter,
                'QgsLayoutItemPicture': QgsLayoutItemPicture,
                'QgsLayoutPoint': QgsLayoutPoint,
                'QgsLayoutSize': QgsLayoutSize,
                'QgsUnitTypes': QgsUnitTypes,
                'QgsLayoutItemPage': QgsLayoutItemPage,
                'QgsLayoutItemScaleBar': QgsLayoutItemScaleBar,
                'QgsLayoutItemHtml': QgsLayoutItemHtml,
                'QgsCoordinateReferenceSystem': QgsCoordinateReferenceSystem,
                'QgsMapLayer': QgsMapLayer,
                'QgsFeature': QgsFeature,
                'QgsGeometry': QgsGeometry,
                'QgsPointXY': QgsPointXY,
                'QgsFields': QgsFields,
                'QgsField': QgsField,
                'QgsVectorFileWriter': QgsVectorFileWriter,
                'QgsVectorDataProvider': QgsVectorDataProvider,
                'QgsWkbTypes': QgsWkbTypes,
                'QgsLayerTreeLayer': QgsLayerTreeLayer,
                'QgsLinePatternFillSymbolLayer': QgsLinePatternFillSymbolLayer,
                'QgsSimpleLineSymbolLayer': QgsSimpleLineSymbolLayer,
                'QgsSymbol': QgsSymbol,
                'QgsSingleSymbolRenderer': QgsSingleSymbolRenderer,
                'QgsLayerTreeGroup': QgsLayerTreeGroup,
                'QgsLayerTreeModel': QgsLayerTreeModel,
                'QgsLegendStyle': QgsLegendStyle,
                'QgsExpression': QgsExpression,
                'QgsExpressionContext': QgsExpressionContext,
                'QgsExpressionContextUtils': QgsExpressionContextUtils,
                'QgsTextBackgroundSettings': QgsTextBackgroundSettings,
                'QgsLayoutItemShape': QgsLayoutItemShape,
                'QgsLayoutItemMapGrid': QgsLayoutItemMapGrid,
                'QgsPoint': QgsPoint
            }

            self._initialized = True
            logger.info("=== QGIS INITIALISÉ AVEC SUCCÈS ===")
            return True, None
            
        except Exception as e:
            error_msg = f"Erreur d'initialisation: {e}"
            self.init_errors.append(error_msg)
            logger.error(error_msg)
            return False, error_msg
    
    def _setup_qgis_environment(self):
        """Configurer l'environnement QGIS"""
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        os.environ['QT_DEBUG_PLUGINS'] = '0'
        os.environ['QT_QPA_FONTDIR'] = os.path.join(os.path.dirname(__file__), 'ttf')
        os.environ['QT_NO_CPU_FEATURE'] = 'sse4.1,sse4.2,avx,avx2'
        logger.info("Environnement QGIS configuré")
    
    def is_initialized(self):
        return self._initialized
    
    def get_classes(self):
        if not self._initialized:
            raise Exception("QGIS not initialized")
        return self.classes
    
    def get_errors(self):
        return self.init_errors


class ProjectSessionManager:
    """Classe pour gérer une session de projet persistante (version utilitaire)"""
    
    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.project = None
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.temporary_files = []
    
    def get_project(self, qgs_project_class):
        """Obtenir le projet QGIS pour cette session"""
        if self.project is None:
            self.project = qgs_project_class()
            self.project.setTitle(f"Session Project - {self.session_id}")
        self.last_accessed = datetime.now()
        return self.project
    
    def cleanup(self):
        """Nettoyer les ressources de la session"""
        try:
            if self.project:
                self.project.clear()
                self.project = None
                
            # Supprimer les fichiers temporaires
            for temp_file in self.temporary_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer le fichier temporaire {temp_file}: {e}")
            self.temporary_files = []
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de la session {self.session_id}: {e}")


# Fonctions utilitaires pour le formatage
def format_layer_info(layer):
    """Formater les informations d'une couche de manière détaillée"""
    base_info = {
        'id': layer.id(),
        'name': layer.name(),
        'source': layer.source() if hasattr(layer, 'source') else None,
        'crs': layer.crs().authid() if hasattr(layer, 'crs') and layer.crs().isValid() else None
    }
    
    # Type de couche
    if hasattr(layer, 'type'):
        layer_type = layer.type()
        if layer_type == 0:  # Vector layer
            base_info['type'] = 'vector'
        elif layer_type == 1:  # Raster layer
            base_info['type'] = 'raster'
        else:
            base_info['type'] = 'unknown'
    
    # Calculer l'étendue de manière sûre
    try:
        extent = layer.extent()
        if extent and not extent.isEmpty():
            base_info['extent'] = {
                'xmin': round(extent.xMinimum(), 6),
                'ymin': round(extent.yMinimum(), 6),
                'xmax': round(extent.xMaximum(), 6),
                'ymax': round(extent.yMaximum(), 6),
            }
    except Exception as e:
        logger.warning(f"Erreur lors du calcul de l'étendue de la couche {layer.id()}: {e}")
    
    # Informations spécifiques aux couches vectorielles
    if hasattr(layer, 'featureCount'):
        try:
            base_info['feature_count'] = layer.featureCount()
        except Exception:
            base_info['feature_count'] = 0
    
    # Informations spécifiques aux couches raster
    if hasattr(layer, 'width') and hasattr(layer, 'height'):
        try:
            base_info['width'] = layer.width()
            base_info['height'] = layer.height()
            if hasattr(layer, 'dataProvider') and layer.dataProvider():
                base_info['bands'] = layer.dataProvider().bandCount()
        except Exception:
            base_info['width'] = 0
            base_info['height'] = 0
            base_info['bands'] = 0
    
    # Type de géométrie pour les couches vectorielles
    if hasattr(layer, 'geometryType'):
        try:
            geom_type = layer.geometryType()
            if geom_type == 0:
                base_info['geometry_type'] = 'point'
            elif geom_type == 1:
                base_info['geometry_type'] = 'line'
            elif geom_type == 2:
                base_info['geometry_type'] = 'polygon'
            else:
                base_info['geometry_type'] = 'unknown'
        except Exception:
            base_info['geometry_type'] = 'unknown'
    
    return base_info


def format_project_info(project):
    """Formater les informations d'un projet de manière détaillée"""
    layers_info = []
    for layer_id, layer in project.mapLayers().items():
        layers_info.append(format_layer_info(layer))
    
    return {
        'title': project.title(),
        'file_name': project.fileName(),
        'crs': project.crs().authid() if project.crs() else None,
        'layers': layers_info,
        'layers_count': len(layers_info),
        'created_at': project.createdAt() if hasattr(project, 'createdAt') else None,
        'last_modified': project.lastModified() if hasattr(project, 'lastModified') else None
    }


# Fonctions de géométrie pour les parcelles
def is_clockwise(points):
    """Vérifier si les points sont dans le sens horaire"""
    return sum((p2.x() - p1.x()) * (p2.y() + p1.y()) for p1, p2 in zip(points, points[1:] + [points[0]])) > 0


def shift_to_northernmost(points):
    """Faire commencer la liste par le point le plus au nord"""
    return points[max(range(len(points)), key=lambda i: points[i].y()):] + points[:max(range(len(points)), key=lambda i: points[i].y())]


def calculate_distance(p1, p2):
    """Calculer la distance entre deux points"""
    return math.hypot(p2.x() - p1.x(), p2.y() - p1.y())


def create_polygon_with_vertex_points(layer, output_polygon_layer=None, output_points_layer=None):
    """
    Crée un layer de polygone avec les points sommets nommés B1, B2, B3... 
    dans le sens horaire en commençant par le point le plus au nord.
    """
    from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsVectorFileWriter, QgsWkbTypes
    from PyQt5.QtCore import QVariant
    
    # Obtenir tous les points du layer d'entrée
    points = []
    
    # Pour les différents types de géométries
    for feature in layer.getFeatures():
        geom = feature.geometry()
        if geom.type() == QgsWkbTypes.PointGeometry:
            # Points individuels
            if geom.isMultipart():
                # Multi-points
                for part in geom.asMultiPoint():
                    points.append(part)
            else:
                # Point simple
                points.append(geom.asPoint())
        elif geom.type() == QgsWkbTypes.LineGeometry:
            # Lignes - extraire les sommets
            if geom.isMultipart():
                # Multi-lignes
                for part in geom.asMultiPolyline():
                    points.extend(part)
            else:
                # Ligne simple
                points.extend(geom.asPolyline())
        elif geom.type() == QgsWkbTypes.PolygonGeometry:
            # Polygones - extraire les sommets
            if geom.isMultipart():
                # Multi-polygones
                for part in geom.asMultiPolygon():
                    for ring in part:
                        points.extend(ring)
            else:
                # Polygone simple
                for ring in geom.asPolygon():
                    points.extend(ring)
    
    if len(points) < 3:
        raise Exception("Il faut au moins 3 points pour créer un polygone")
    
    # Traitement des points
    points = list(filter(None, points))
    if not points:
        raise ValueError("Aucun point valide trouvé dans le fichier.")

    sorted_points = list(dict.fromkeys(points))
    if not is_clockwise(sorted_points):
        sorted_points.reverse()
    sorted_points = shift_to_northernmost(sorted_points)
    
    # Créer le polygone
    polygon_geom = QgsGeometry.fromPolygonXY([sorted_points])
    
    # Créer le layer polygone
    polygon_layer = QgsVectorLayer("Polygon?crs=" + layer.crs().authid(), "Terrain", "memory")
    polygon_provider = polygon_layer.dataProvider()
    
    # Ajouter les champs nécessaires
    polygon_provider.addAttributes([
        QgsField("id", QVariant.String),
        QgsField("Superficie", QVariant.Double)
    ])
    polygon_layer.updateFields()
    
    # Créer la feature du polygone
    polygon_feature = QgsFeature()
    polygon_feature.setGeometry(polygon_geom)
    area_m2 = polygon_geom.area()
    polygon_feature.setAttributes([1, area_m2])
    
    # Ajouter la feature au layer
    polygon_provider.addFeatures([polygon_feature])
    
    # Créer le layer de points
    points_layer = QgsVectorLayer("Point?crs=" + layer.crs().authid(), "Points sommets", "memory")
    points_provider = points_layer.dataProvider()
    
    # Ajouter les champs nécessaires
    points_provider.addAttributes([
        QgsField(n, t) for n, t in [
            ("Bornes", QVariant.String), 
            ("X", QVariant.Int), 
            ("Y", QVariant.Int), 
            ("Distance", QVariant.Double)
        ]
    ])
    points_layer.updateFields()
    
    # Créer les features de points
    point_features = []
    for i, point in enumerate(sorted_points):
        point_feature = QgsFeature()
        point_feature.setGeometry(QgsGeometry.fromPointXY(point))
        point_feature.setAttributes([
            f"B{i+1}", 
            int(point.x()), 
            int(point.y()), 
            round(calculate_distance(point, sorted_points[(i+1) % len(sorted_points)]), 2)
        ])
        point_features.append(point_feature)
    
    # Ajouter les features au layer de points
    points_provider.addFeatures(point_features)
    
    # Sauvegarder les layers si des chemins sont fournis
    if output_polygon_layer:
        QgsVectorFileWriter.writeAsVectorFormat(
            polygon_layer, output_polygon_layer, "UTF-8", 
            polygon_layer.crs(), "ESRI Shapefile"
        )
    
    if output_points_layer:
        QgsVectorFileWriter.writeAsVectorFormat(
            points_layer, output_points_layer, "UTF-8", 
            points_layer.crs(), "ESRI Shapefile"
        )
    
    return polygon_layer, points_layer


def create_print_layout_with_qgs(layout_name, project, map_items_config=None):
    """
    Créer un layout QGIS avec QgsPrintLayout pour générer des PDF professionnels
    """
    try:
        # Obtenir les classes QGIS
        classes = get_qgis_manager().get_classes()
        QgsLayoutItemMap = classes['QgsLayoutItemMap']
        QgsLayoutItemLegend = classes['QgsLayoutItemLegend']
        QgsLayoutItemLabel = classes['QgsLayoutItemLabel']
        QgsLayoutItemScaleBar = classes['QgsLayoutItemScaleBar']
        QgsLayoutItemPage = classes['QgsLayoutItemPage']
        QgsPrintLayout = classes['QgsPrintLayout']
        QgsUnitTypes = classes['QgsUnitTypes']
        QgsLayoutPoint = classes['QgsLayoutPoint']
        QgsLayoutSize = classes['QgsLayoutSize']
        
        from PyQt5.QtGui import QFont
        from PyQt5.QtCore import Qt
        
        locale.setlocale(locale.LC_TIME, "fr_FR")
        date = datetime.now().strftime(r"%d %B %Y")
        
        # Créer un nouveau layout
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        
        pc = layout.pageCollection()
        page = pc.pages()[0]
        page.setPageSize("A4", QgsLayoutItemPage.Portrait)
        
        data = [
            {"text": "MINISTERE DE L'ECONOMIE ET DES FINANCES", "x": 5, "y": 5, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 12, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "SECRETARIAT GENERAL", "x": 5, "y": 17, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 22, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "DIRECTION GENERALE DES IMPOTS", "x": 10, "y": 27, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 32, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "DIRECTION REGIONALE DES IMPOTS DU GUIRIKO", "x": 5, "y": 39, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 46, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "SERVICE DU CADASTRE ET DES TRAVAUX FONCIERS DU GUIRIKO", "x": 5, "y": 53, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 60, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": f"N°......./MEF/SG/DGI/DRI-GRK/SCTF-GRK", "x": 10, "y": 75, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "BURKINA FASO", "x": 120, "y": 5, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "La Patrie ou la Mort, Nous vaincrons", "x": 120, "y": 10, "width": 90, "height": 10, "font_size": 10, "is_bold": 1},
            {"text": f"Bobo-Dioulasso le {date}", "x": 120, "y": 30, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "FICHE D'IDENTIFICATION CADASTRALE", "x": 5, "y": 105, "width": 200, "height": 10, "font_size": 24, "is_bold": 1},
        ]
        
        for d in data:
            A = QgsLayoutItemLabel(layout)
            A.setText(d['text'])
            A.setFont(QFont("Times New Roman", d['font_size'], QFont.Bold if d['is_bold'] == 1 else QFont.Normal))
            A.setHAlign(Qt.AlignCenter)
            A.setVAlign(Qt.AlignCenter)
            A.attemptMove(QgsLayoutPoint(d['x'], d['y'], QgsUnitTypes.LayoutMillimeters))
            A.attemptResize(QgsLayoutSize(d['width'], d['height'], QgsUnitTypes.LayoutMillimeters))
            layout.addItem(A)
            
        return layout
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du layout: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def create_print_layout_croquis(layout_name, project, map_items_config=None):
    """Créer un layout de croquis avec cartes et légendes"""
    try:
        classes = get_qgis_manager().get_classes()
        QgsPrintLayout = classes['QgsPrintLayout']
        QgsLayoutItemMap = classes['QgsLayoutItemMap']
        QgsLayoutItemLegend = classes['QgsLayoutItemLegend']
        QgsLayoutPoint = classes['QgsLayoutPoint']
        QgsUnitTypes = classes['QgsUnitTypes']
        QgsLayoutSize = classes['QgsLayoutSize']
        
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        
        # Logic pour créer le croquis serait ici
        # Version simplifiée pour l'exemple
        
        return layout
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du layout croquis: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def generate_pdf_from_layout(layout, output_path):
    """Générer un PDF à partir d'un QgsPrintLayout"""
    try:
        # Obtenir les classes QGIS
        classes = get_qgis_manager().get_classes()
        QgsLayoutExporter = classes['QgsLayoutExporter']
        
        # Exporter le layout en PDF
        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToPdf(output_path)
        
        if result == QgsLayoutExporter.Success:
            return True, output_path
        else:
            return False, f"Erreur d'exportation PDF: {result}"
            
    except Exception as e:
        return False, str(e)