from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QVBoxLayout, QWidget, QPushButton, QLabel, QGraphicsItem
)
from PySide6.QtCore import Qt, QRectF, QPoint, Signal,Slot
from PySide6.QtGui import QWheelEvent, QMouseEvent, QPainter, QTransform, QColor
from graphicsScenes import GameState
from graphicItems import BaseTowerItem

TOWER_TYPES = {
    "basic": {
        "name": "Basic Tower",
        "type": "basic",
        "cost": 100,
        "icon": "path/to/basic_tower_icon.png",
        "description": "Basic tower with moderate damage."
    },
    "sniper": {
        "name": "Sniper Tower",
        "type": "sniper",
        "cost": 200,
        "icon": "path/to/sniper_tower_icon.png",
        "description": "Long-range tower with high damage."
    },
}


class TowerStoreWidget(QWidget):
    tower_selected = Signal(dict)  # Emit when a tower is selected
    def __init__(self, game_state : GameState):
        super().__init__()
        self.game_state = game_state
        self.init_ui()

    def init_ui(self):
        self.setFixedWidth(200)
        layout = QVBoxLayout()
        
        # Gold Display
        self.gold_label = QLabel(f"Gold: {self.game_state.gold}")
        layout.addWidget(self.gold_label)
        ## Lives Display
        self.lives_label = QLabel(f"Lives: {self.game_state.lives}")
        layout.addWidget(self.lives_label)
        
        # Tower Buttons
        self.tower_buttons = []
        for tower in TOWER_TYPES.values():
            btn = QPushButton(self.create_button_content(tower))
            btn.setProperty('cost', tower['cost'])
            btn.setEnabled(False)
            btn.clicked.connect(lambda _, t=tower: self.handle_tower_selection(t))
            self.tower_buttons.append(btn)
            layout.addWidget(btn)
        
        self.setLayout(layout)

    def create_button_content(self, tower):
        return f"""
        <div style='text-align: center'>
            <img src='{tower["icon"]}' width=64>
            <br>{tower["name"]}
            <br>Cost: {tower["cost"]}g
        </div>
        """

    def handle_tower_selection(self, tower):
        """Emit signal when a tower is selected"""
        self.tower_selected.emit(tower)
        
    def update_store_ui(self, gold):
        """Update the store UI based on game state"""
        self.gold_label.setText(f"Gold: {gold}")
        for btn in self.tower_buttons:
            cost = btn.property('cost')
            btn.setEnabled(gold >= cost)
    def update_lives_ui(self, lives):
        """Update the lives UI based on game state"""
        self.lives_label.setText(f"Lives: {lives}")
class TowerOverviewWidget(QWidget):
    sell_tower = Signal(object)  # Emit when the sell button is clicked
    upgrade_tower = Signal(object)  # Emit when the upgrade button is clicked
    def __init__(self):
        super().__init__()
        self.tower= BaseTowerItem(QPoint(0.0,0.0))
        self.hide()
        self.init_ui()
    def init_ui(self):
        self.setFixedWidth(200)
        layout = QVBoxLayout()

        self.name_label = QLabel("Tower Name")
        self.kills_label = QLabel("Kills: 0")

        self.sell_btn = QPushButton("Sell")
        self.sell_btn.clicked.connect(self.handle_sell_tower)
        self.upgrade_btn = QPushButton("Upgrade")
        self.upgrade_btn.clicked.connect(self.handle_upgrade_tower)
        self.upgrade_btn.setEnabled(False)
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.kills_label)
        layout.addWidget(self.sell_btn)
        layout.addWidget(self.upgrade_btn)
        self.setLayout(layout)
    @Slot(object)
    def update_overview_ui(self, tower):
        """Display tower overview"""
        if(tower is None):
            self.tower.show_range = False
            self.clear()
            return
        self.tower = tower
        self.name_label.setText(f"Name: {tower.name}")  
        self.kills_label.setText(f"Kills: {tower.kills}")
        self.show()
    def handle_sell_tower(self):
        """Handle tower sell action"""
        self.sell_tower.emit(self.tower)
        self.hide()
    def handle_upgrade_tower(self):
        """Handle tower upgrade action"""
        self.upgrade_tower.emit(self.tower)
        self.hide()
    def clear(self):
        self.tower = None
        self.hide()
        
class GameView(QGraphicsView):
    viewport_changed = Signal(QRectF)  # Emits visible area changes
    tower_selected = Signal(QGraphicsItem)  # Emits when a tower is selected
    
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
        if selected and isinstance(selected[0], BaseTowerItem):
            print(f"Selected item: {selected[0].__class__.__name__}")
            self.tower_selected.emit(selected[0])
            pass
        else:
            self.tower_selected.emit(None)
    
        