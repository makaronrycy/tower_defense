from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QVBoxLayout, QWidget, QPushButton, QLabel, QGraphicsItem
, QGraphicsTextItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsEllipseItem,QRadioButton,QButtonGroup, QGroupBox, QTextEdit, QLineEdit
)
from PySide6.QtCore import Qt, QRectF, QPoint, Signal,Slot
from PySide6.QtGui import QWheelEvent, QMouseEvent, QPainter, QTransform, QColor,QFont
from PySide6.QtCore import QTimer, QPointF
from graphicsScenes import GameState
from graphicItems import BaseTowerItem
from network import GameNetworkEvent
import time

TOWER_TYPES = {
    "basic": {
        "name": "Basic Tower",
        "type": "basic",
        "cost": 20,
        "description": "Basic tower with moderate damage."
    },
    "bomb": {
        "name": "Bomb Tower",
        "type": "bomb",
        "cost": 200,
        "description": "Bomb tower with splash damage."
    },
    "booster": {
        "name": "Booster Tower",
        "type": "booster",
        "cost": 100,
        "description": "Booster tower that increases stats and reduces upgrade cost."
    },
}


class TowerStoreWidget(QWidget):
    tower_selected = Signal(dict)  # Emit when a tower is selected
    wave_started = Signal()  # Emit when a wave starts
    game_saved = Signal()  # Emit when the game is paused
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
            btn = QPushButton(self.create_button_content(tower),)
            btn.toolTip = tower['description']
            btn.setFixedSize(150, 50)
            btn.setStyleSheet("background-color: lightblue;")
            btn.setProperty('cost', tower['cost'])
            cost = btn.property('cost')
            btn.setEnabled(self.game_state.gold >= cost)
            btn.clicked.connect(lambda _, t=tower: self.handle_tower_selection(t))
            self.tower_buttons.append(btn)
            layout.addWidget(btn)
        self.waveButton = QPushButton("Start Wave")
        self.waveButton.clicked.connect(self.handle_wave_start)
        self.saveButton = QPushButton("Save")
        self.saveButton.clicked.connect(self.handle_save)
        
        layout.addWidget(self.waveButton)
        layout.addWidget(self.saveButton)
        self.setLayout(layout)

    def create_button_content(self, tower):
        return f"""
            {tower["name"]}
            Cost: {tower["cost"]}g
        """
    def handle_wave_start(self):
        """Emit signal when a wave starts"""
        self.waveButton.setEnabled(False)
        self.waveButton.setText("Wave Started")
        self.wave_started.emit()
    def handle_wave_end(self):
        self.waveButton.setEnabled(True)
        self.waveButton.setText(f"Start Wave {self.game_state.wave + 1}")
    def handle_save(self):
        """Emit signal when the game is saved"""
        self.game_saved.emit()
    def handle_tower_selection(self, tower):
        """Emit signal when a tower is selected"""
        self.tower_selected.emit(tower)
    def handle_game_over(self):
        """Handle game over state"""
        self.waveButton.setEnabled(False)
        self.pauseButton.setEnabled(False)
        for btn in self.tower_buttons:
            btn.setEnabled(False)
        self.waveButton.setText("Game Over")
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
    tower_deselected = Signal()  # Emit when a tower is selected
    def __init__(self,game_state : GameState):
        super().__init__()
        self.tower= BaseTowerItem(QPoint(0.0,0.0))
        self.game_state = game_state
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.hide()
        self.init_ui()
    def init_ui(self):
        self.setFixedWidth(200)
        layout = QVBoxLayout()

        self.name_label = QLabel("Tower Name")
        self.kills_label = QLabel("Kills: 0")
        self.frame_label = QLabel(f"Frame: {self.tower.current_frame}")
        self.sell_btn = QPushButton(f"Sell:{self.tower.cost}")
        self.sell_btn.clicked.connect(self.handle_sell_tower)
        self.upgrade_btn = QPushButton(f"Upgrade:{self.tower.upgrade_cost} ")
        self.upgrade_btn.clicked.connect(self.handle_upgrade_tower)
        self.upgrade_btn.setEnabled(self.game_state.gold >= self.tower.upgrade_cost)
        
        layout.addWidget(self.frame_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.kills_label)
        layout.addWidget(self.sell_btn)
        layout.addWidget(self.upgrade_btn)
        self.setLayout(layout)
    @Slot(object)
    def update_overview_ui(self, tower):
        """Display tower overview"""
        if(tower is None):
            self.clear()
            return
        self.tower = tower
        
        self.name_label.setText(f"Name: {tower.name}")
        self.frame_label.setText(f"Frame: {tower.animations.current_frame}")
        self.sell_btn.setText(f"Sell: {tower.cost // 2}")
        self.upgrade_btn.setText(f"Upgrade: {tower.upgrade_cost}")
        self.kills_label.setText(f"Kills: {tower.kills}")
        self.show()
    @Slot(int)
    def update_upgrade_ui(self, gold):
        if self.tower:
            self.upgrade_btn.setEnabled(gold >= self.tower.upgrade_cost)
        else:
            self.upgrade_btn.setEnabled(False)
    def handle_sell_tower(self):
        """Handle tower sell action"""

        self.sell_tower.emit(self.tower)
        self.tower_deselected.emit()
        self.hide()
    def handle_upgrade_tower(self):
        """Handle tower upgrade action"""
        self.upgrade_tower.emit(self.tower)
        self.tower_deselected.emit()
        self.hide()
    def clear(self):
        self.tower = None
        self.tower_deselected.emit()
        self.hide()

# class TitleScene(QGraphicsScene):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setSceneRect(0, 0, 800, 600)
#         self.setBackgroundBrush(QColor(255, 255, 255))  # Set background color to white

#         # Add title text
#         title_text = "Tower Defense Game"
#         title_item = QGraphicsTextItem(title_text)
#         title_item.setFont(QFont("Arial", 24))
#         title_item.setDefaultTextColor(QColor(0, 0, 0))  # Set text color to black
#         title_item.setPos(300, 250)  # Center the text
#         self.addItem(title_item)

#         self.button_group = QButtonGroup(self)
#         # Add buttons for different game modes
#         # Add single player button
#         single_player_button = QRadioButton("Single Player")
#         single_player_button.setGeometry(300, 350, 200, 50)
#         single_player_button.setStyleSheet("background-color: lightblue;")
#         single_player_button.setChecked(True)
#         self.button_group.addButton(single_player_button)
#         self.addWidget(single_player_button)
#         # Add multiplayer button
#         multiplayer_button = QRadioButton("Multiplayer")
#         multiplayer_button.setGeometry(300, 400, 200, 50)
#         multiplayer_button.setStyleSheet("background-color: lightblue;")
#         self.button_group.addButton(multiplayer_button)
#         self.addWidget(multiplayer_button)
#         # Add local multiplayer button
#         local_multiplayer_button = QRadioButton("Local Multiplayer")
#         local_multiplayer_button.setGeometry(300, 450, 200, 50)
#         local_multiplayer_button.setStyleSheet("background-color: lightblue;")
#         self.button_group.addButton(local_multiplayer_button)
#         self.addWidget(local_multiplayer_button)
        
#         # Add start button
#         start_button = QPushButton("Start Game")
#         start_button.setGeometry(300, 500, 200, 50)
#         start_button.setStyleSheet("background-color: lightblue;")
#         start_button.clicked.connect(self.start_game)
#         self.addWidget(start_button)


#         # Add exit button
#         exit_button = QPushButton("Exit")
#         exit_button.setGeometry(350, 450, 100, 50)
#         exit_button.setStyleSheet("background-color: lightblue;")
#         exit_button.clicked.connect(self.exit_game)
#         self.addWidget(exit_button)
    def start_game(self):
        """Start the game and switch to the main scene"""
        selected_button = self.button_group.checkedButton()
        if selected_button:
            game_mode = selected_button.text()
            print(f"Selected Game Mode: {game_mode}")
            # Emit signal or handle game mode selection here
            self.parent().start_game(game_mode)
        

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


    def repaint_view(self):
        """Repaint the view to reflect changes in the scene"""
        self.repaint()
    def _setup_view(self):
        """Configure view rendering and behavior"""
        self.setScene(self._scene)
        self.setRenderHints(
            QPainter.TextAntialiasing
        )

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.scale(1.5,1.5)
        # Enable OpenGL acceleration if available
        try:
            from PySide6.QtOpenGLWidgets import QOpenGLWidget
            self.setViewport(QOpenGLWidget())
        except ImportError:
            pass
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

    # def _handle_selection(self):
    #     """Forward selection changes to scene"""
    #     selected = self.scene().selectedItems()
    #     if selected and isinstance(selected[0], BaseTowerItem):
    #         print(f"Selected item: {selected[0].__class__.__name__}")
    #         self.tower_selected.emit(selected[0])
    #         pass
    #     else:
    #         self.tower_selected.emit(None)

# Add this class

class MultiplayerInfoWidget(QWidget):
    """Widget to display multiplayer game information"""
    
    send_chat = Signal(str)  # For chat messages
    
    def __init__(self, game_scene):
        super().__init__()
        self.game_scene = game_scene
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Player information
        self.player_info = QGroupBox("Players")
        player_layout = QVBoxLayout()
        
        self.player1_label = QLabel("Player 1 (Left Side)")
        self.player1_label.setStyleSheet("color: blue; font-weight: bold;")
        
        self.player2_label = QLabel("Player 2 (Right Side)")
        self.player2_label.setStyleSheet("color: gray;")
        
        player_layout.addWidget(self.player1_label)
        player_layout.addWidget(self.player2_label)
        self.player_info.setLayout(player_layout)
        
        # Chat section
        self.chat_box = QGroupBox("Chat")
        chat_layout = QVBoxLayout()
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type message and press Enter...")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        
        chat_layout.addWidget(self.chat_history)
        chat_layout.addWidget(self.chat_input)
        self.chat_box.setLayout(chat_layout)
        
        # Add to main layout
        layout.addWidget(self.player_info)
        layout.addWidget(self.chat_box)
        
        # Network status indicator
        self.status_label = QLabel("Connected")
        self.status_label.setStyleSheet("color: green;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Connect signals from game scene
        self.game_scene.player_joined.connect(self.on_player_joined)
        self.game_scene.player_left.connect(self.on_player_left)
        self.game_scene.network_event.connect(self.on_network_event)
    
    def on_player_joined(self, player_id):
        """Handle player join event"""
        self.player2_label.setStyleSheet("color: green; font-weight: bold;")
        self.add_chat_message("System", f"Player {player_id} has joined the game")
    
    def on_player_left(self, player_id):
        """Handle player leave event"""
        self.player2_label.setStyleSheet("color: gray;")
        self.add_chat_message("System", f"Player {player_id} has left the game")
    
    def on_network_event(self, event):
        """Handle various network events"""
        if event["type"] == GameNetworkEvent.CHAT_MESSAGE:
            sender = event["player_id"]
            message = event["data"]["message"]
            self.add_chat_message(sender, message)
    
    def add_chat_message(self, sender, message):
        """Add message to chat history"""
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {sender}: {message}"
        self.chat_history.append(formatted)
    
    def send_chat_message(self):
        """Send chat message"""
        message = self.chat_input.text().strip()
        if message:
            self.chat_input.clear()
            # Send via network manager
            self.game_scene.network.send_event(GameNetworkEvent.CHAT_MESSAGE, {
                "message": message
            })
            # Add to local chat (our own messages)
            player_id = self.game_scene.player_id or "You"
            self.add_chat_message(player_id, message)

