from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView
from graphicItems import BaseItem
from PySide6.QtGui import QColor
from graphicsScenes import GameScene

from PySide6.QtCore import Qt, QRectF, QTimer, QPoint, Signal
from PySide6.QtWidgets import QGraphicsView, QApplication
from PySide6.QtGui import QWheelEvent, QMouseEvent, QPainter, QTransform

class GameView(QGraphicsView):
    viewport_changed = Signal(QRectF)  # Emits visible area changes
    
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self._scene = scene
        self._zoom_level = 1.0
        self._pan_start = QPoint()
        self._panning = False
        
        # Initialize view settings
        self._setup_view()
        self._connect_signals()

    def _setup_view(self):
        """Configure view rendering and behavior"""
        self.setScene(self._scene)
        self.setRenderHints(
            QPainter.Antialiasing |
            QPainter.SmoothPixmapTransform |
            QPainter.TextAntialiasing
        )
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        
        # Enable OpenGL acceleration if available
        try:
            from PySide6.QtOpenGLWidgets import QOpenGLWidget
            self.setViewport(QOpenGLWidget())
        except ImportError:
            pass

    def _connect_signals(self):
        """Connect internal signals"""
        self.scene().selectionChanged.connect(self._handle_selection)
        self.viewport_changed.connect(self._scene.update_viewport)

    # --------------------------
    # View Manipulation Methods
    # --------------------------
    def wheelEvent(self, event: QWheelEvent):
        """Handle zoom with mouse wheel"""
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.zoom_in(zoom_factor)
        else:
            self.zoom_out(1/zoom_factor)

    def mousePressEvent(self, event: QMouseEvent):
        """Start panning with middle mouse button"""
        if event.button() == Qt.MiddleButton:
            self._pan_start = event.pos()
            self._panning = True
            self.setCursor(Qt.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle view panning"""
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """End panning operation"""
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)

    # --------------------------
    # Zoom Controls
    # --------------------------
    def zoom_in(self, factor=1.1):
        """Zoom the view in"""
        self._apply_zoom(factor)

    def zoom_out(self, factor=0.9):
        """Zoom the view out"""
        self._apply_zoom(factor)

    def reset_zoom(self):
        """Reset to default zoom level"""
        self.setTransform(QTransform())
        self._zoom_level = 1.0

    def _apply_zoom(self, factor):
        """Internal zoom implementation"""
        self.scale(factor, factor)
        self._zoom_level *= factor
        self.viewport_changed.emit(self.viewport_rect())

    # --------------------------
    # Viewport Management
    # --------------------------
    def viewport_rect(self) -> QRectF:
        """Get visible area in scene coordinates"""
        return self.mapToScene(self.viewport().rect()).boundingRect()

    def center_on_scene(self):
        """Center view on game scene"""
        self.centerOn(self.scene().sceneRect().center())

    def fit_scene(self):
        """Fit entire scene in view"""
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

    # --------------------------
    # Performance Optimizations
    # --------------------------
    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Custom background rendering"""
        # Add grid drawing here if needed
        super().drawBackground(painter, rect)

    def item_proxy(self, item):
        """Create a proxy widget for HUD elements"""
        return self.scene().addWidget(item)

    # --------------------------
    # Debug Features
    # --------------------------
    def toggle_debug_mode(self, enable: bool):
        """Toggle debug overlay"""
        if enable:
            self.setRenderHints(self.renderHints() | QPainter.Debug)
        else:
            self.setRenderHints(self.renderHints() & ~QPainter.Debug)

    def _handle_selection(self):
        """Forward selection changes to scene"""
        selected = self.scene().selectedItems()
        if selected:
            self._scene.tower_selected.emit(selected[0])
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tower Defense")
        self.setGeometry(100, 100, 800, 600)

        
        self.start_button = QPushButton("Start Game", self)
        self.start_button.setGeometry(350, 250, 100, 50)
        self.start_button.clicked.connect(self.start_game)

    @Slot()
    def start_game(self):
        #change scene
        self.scene = GameScene()
        self.view = GameView()
        self.view.setScene(self.scene)
        
        self.setCentralWidget(self.view)
        
        print("Game Started")

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    
    app.exec()
