from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView,QLabel,QVBoxLayout,QWidget
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QPushButton, QGraphicsView
from PySide6.QtWidgets import QProgressBar, QGroupBox

from PySide6.QtWidgets import QMainWindow,  QDialog, QFormLayout, QSpinBox, QCheckBox,QMessageBox
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtCore import Qt, QRectF, QTimer, QPoint, Signal,QObject
from PySide6.QtWidgets import QGraphicsView, QApplication
from PySide6.QtGui import QWheelEvent, QMouseEvent, QPainter, QTransform, QAction
from ui import GameView, TowerStoreWidget,TowerOverviewWidget,MultiplayerInfoWidget

from config_dialog import ConfigurationDialog
from graphicsScenes import GameScene, GameState
from tower_defense_ai import TowerDefenseAI, TrainingWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tower Defense")
        self.create_menu_bar()

        self.scene = GameScene()
        self.view = GameView(self.scene)
        self.store = TowerStoreWidget(self.scene.game_state)
        self.tower_overview =TowerOverviewWidget(self.scene.game_state)

        self.setup_common_connections()
        splitter = QSplitter()
        splitter.addWidget(self.tower_overview)
        splitter.addWidget(self.view)
        splitter.addWidget(self.store)
        self.setCentralWidget(splitter)

        QTimer.singleShot(1000, self.scene.start_game)
    def create_menu_bar(self):
        """Create the application menu bar"""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Configuration action
        config_action = QAction("Configuration", self)
        config_action.triggered.connect(self.show_configuration_dialog)
        file_menu.addAction(config_action)

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def show_configuration_dialog(self):
        """Show the configuration dialog"""
        dialog = ConfigurationDialog(self, self.scene)
        dialog.config_saved.connect(self.apply_configuration)
        
        # Add internet connection button
        dialog.add_internet_button()
        dialog.internet_button.clicked.connect(self.show_internet_dialog)
        
        dialog.exec()

    def show_internet_dialog(self):
        """Show the internet connection dialog"""
        from connection_dialog import ConnectionDialog
        
        dialog = ConnectionDialog(self)
        dialog.connection_ready.connect(self.handle_internet_connection)
        dialog.exec()

    def handle_internet_connection(self, settings):
        """Handle internet connection settings"""
        if settings["is_host"]:
            # Create a configuration for hosting
            config = {
                "game_mode": "network_game",
                "is_host": True,
                "server_port": settings["port"]
            }
        else:
            # Create a configuration for joining
            config = {
                "game_mode": "network_game",
                "is_host": False,
                "server_ip": settings["ip"],
                "server_port": settings["port"]
            }
        
        # Apply the configuration
        self.apply_config(config)

    @Slot(dict)
    def apply_configuration(self, config):
        """Apply the saved configuration to the game"""
        print(f"Applying configuration: {config}")
        self.apply_config(config)

    def apply_config(self, config):
        """Apply configuration settings"""
        game_mode = config.get("game_mode", "single_player")
        
        # Clear existing scene and create a new one
        if self.scene:
            self.scene.deleteLater()
        
        if game_mode == "network_game":
            # Setup network game
            is_host = config.get("is_host", False)
            self.scene = GameScene(self, multiplayer=True, is_host=is_host)
            self.view.setScene(self.scene)
            
            # Connect signals
            self.setup_common_connections()
            
            # Setup network
            if is_host:
                success = self.scene.network.host_game(int(config.get("server_port", 5555)))
                if not success:
                    QMessageBox.critical(self, "Network Error", "Failed to host game")
                    return
            else:
                server_ip = config.get("server_ip", "127.0.0.1")
                port = int(config.get("server_port", 5555))
                success = self.scene.network.join_game(server_ip, port)
                if not success:
                    QMessageBox.critical(self, "Network Error", "Failed to join game")
                    return
                    
            # Show waiting dialog if hosting
            if is_host:
                QMessageBox.information(self, "Waiting for Player", 
                                       "Waiting for another player to join...")
        
        elif game_mode == "local_multiplayer":
            # Setup local multiplayer game
            self.scene = GameScene(self, multiplayer=True, is_host=True)
            self.view.setScene(self.scene)
            self.setup_common_connections()
            
        else:
            # Single player (default)
            self.scene = GameScene(self)
            self.view.setScene(self.scene)
            self.setup_common_connections()
            
        # Add the multiplayer info widget for network games
        if game_mode == "network_game" or game_mode == "local_multiplayer":
            self.multiplayer_info = MultiplayerInfoWidget(self.scene)
            
            # Replace layout:
            splitter = QSplitter()
            splitter.addWidget(self.tower_overview)
            splitter.addWidget(self.view)
            
            right_panel = QWidget()
            right_layout = QVBoxLayout(right_panel)
            right_layout.addWidget(self.store)
            right_layout.addWidget(self.multiplayer_info)
            
            splitter.addWidget(right_panel)
            self.setCentralWidget(splitter)
        else:
            # Single player layout
            splitter = QSplitter()
            splitter.addWidget(self.tower_overview)
            splitter.addWidget(self.view)
            splitter.addWidget(self.store)
            self.setCentralWidget(splitter)
            
        # Start the game after a short delay
        QTimer.singleShot(1000, self.scene.start_game)

    def setup_common_connections(self):
        """Setup common signal connections for all game modes"""
        self.store = TowerStoreWidget(self.scene.game_state)
        self.tower_overview = TowerOverviewWidget(self.scene.game_state)
        
        # Connect signals
        self.scene.game_state.gold_changed.connect(self.store.update_store_ui)
        self.scene.game_state.gold_changed.connect(self.tower_overview.update_upgrade_ui)
        self.scene.game_state.lives_changed.connect(self.store.update_lives_ui)
        self.scene.game_state.record_changed.connect(self.hide_uis)
        self.scene.tower_selected.connect(self.tower_overview.update_overview_ui)
        self.scene.repaint_view.connect(self.view.repaint_view)
        
        self.store.tower_selected.connect(self.scene.start_tower_placement)
        self.tower_overview.sell_tower.connect(self.scene.handle_tower_sale)
        self.tower_overview.upgrade_tower.connect(self.scene.handle_tower_upgrade)
        self.tower_overview.tower_deselected.connect(self.scene.handle_tower_deselection)
        self.scene.tower_selected.connect(self.scene.handle_tower_selection)
        
        self.store.wave_started.connect(self.scene.start_wave)
        self.scene.game_over_signal.connect(self.store.handle_game_over)
        self.scene.wave_ended.connect(self.store.handle_wave_end)
        
        # Add AI controls if they don't exist yet
        if not hasattr(self, 'ai_panel'):
            ai_controls = self.create_ai_controls()
            
            # Add AI controls to layout
            if hasattr(self, 'multiplayer_info'):
                # Multiplayer mode
                right_panel = self.multiplayer_info.parent()
                right_layout = right_panel.layout()
                right_layout.addWidget(ai_controls)
            else:
                # Single player mode
                right_panel = self.store
                if isinstance(right_panel, QSplitter):
                    # Create a container for store and AI controls
                    container = QWidget()
                    container_layout = QVBoxLayout(container)
                    container_layout.addWidget(self.store)
                    container_layout.addWidget(ai_controls)
                    
                    # Replace store with container in splitter
                    index = right_panel.indexOf(self.store)
                    right_panel.replaceWidget(index, container)
                else:
                    # Store already in a container
                    right_layout = right_panel.layout()
                    right_layout.addWidget(ai_controls)
        
        # Initialize AI for the new scene
        self.initialize_ai()

    def hide_uis(self):
        """Hide the UI elements when the game is over"""
        self.store.hide()
        self.tower_overview.hide()
        self.multiplayer_info.hide()

    def create_ai_controls(self):
        """Create AI control panel"""
        self.ai_panel = QGroupBox("AI Controls")
        layout = QVBoxLayout()
        
        # AI Buttons
        buttons_layout = QHBoxLayout()
        self.ai_play_button = QPushButton("AI Play")
        self.ai_stop_button = QPushButton("Stop AI")
        self.ai_train_button = QPushButton("Train AI")
        
        self.ai_play_button.clicked.connect(self.start_ai_play)
        self.ai_stop_button.clicked.connect(self.stop_ai_play)
        self.ai_train_button.clicked.connect(self.train_ai)
        
        # Disable stop button initially
        self.ai_stop_button.setEnabled(False)
        
        buttons_layout.addWidget(self.ai_play_button)
        buttons_layout.addWidget(self.ai_stop_button)
        buttons_layout.addWidget(self.ai_train_button)
        
        # AI Status
        self.ai_status = QLabel("AI Status: Idle")
        
        # Progress Bar for training
        self.training_progress = QProgressBar()
        self.training_progress.setVisible(False)
        
        layout.addLayout(buttons_layout)
        layout.addWidget(self.ai_status)
        layout.addWidget(self.training_progress)
        
        self.ai_panel.setLayout(layout)
        return self.ai_panel

    def initialize_ai(self):
        """Initialize the AI controller"""
        self.ai = TowerDefenseAI(self.scene)
        
        # Connect signals
        self.ai.action_performed.connect(self.on_ai_action)
        self.ai.thinking.connect(lambda: self.ai_status.setText("AI Status: Thinking..."))

    def start_ai_play(self):
        """Start AI playing the game"""
        if not hasattr(self, 'ai'):
            self.initialize_ai()
        
        # Check if model exists or needs to be created
        model_exists = self.ai.load_model()
        
        if not model_exists:
            reply = QMessageBox.question(
                self, "No AI Model Found", 
                "No trained AI model found. Do you want to train one now?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.train_ai()
                return
        
        # Start AI playing
        self.ai.start()
        self.ai_status.setText("AI Status: Playing")
        
        # Update button states
        self.ai_play_button.setEnabled(False)
        self.ai_stop_button.setEnabled(True)
        self.ai_train_button.setEnabled(False)

    def stop_ai_play(self):
        """Stop AI playing"""
        if hasattr(self, 'ai'):
            self.ai.stop()
        
        self.ai_status.setText("AI Status: Stopped")
        
        # Update button states
        self.ai_play_button.setEnabled(True)
        self.ai_stop_button.setEnabled(False)
        self.ai_train_button.setEnabled(True)

    def train_ai(self):
        """Start training the AI"""
        if not hasattr(self, 'ai'):
            self.initialize_ai()
        
        # Ask for training parameters
        reply = QMessageBox.question(
            self, "Train AI", 
            "Training may take a while. Continue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.No:
            return
        
        # Setup progress tracking
        self.training_progress.setValue(0)
        self.training_progress.setVisible(True)
        self.ai_status.setText("AI Status: Training...")
        
        # Disable all AI buttons during training
        self.ai_play_button.setEnabled(False)
        self.ai_stop_button.setEnabled(False)
        self.ai_train_button.setEnabled(False)
        
        # Create training worker thread
        self.training_worker = TrainingWorker(self.ai, timesteps=50000)
        self.training_worker.progress.connect(self.update_training_progress)
        self.training_worker.completed.connect(self.on_training_completed)
        
        # Start training in background
        self.training_worker.start()

    def update_training_progress(self, progress):
        """Update the training progress bar"""
        self.training_progress.setValue(progress)

    def on_training_completed(self, success):
        """Handle training completion"""
        self.training_progress.setVisible(False)
        
        # Re-enable buttons
        self.ai_play_button.setEnabled(True)
        self.ai_train_button.setEnabled(True)
        
        if success:
            self.ai_status.setText("AI Status: Training Completed")
            QMessageBox.information(self, "Training Complete", 
                                  "AI training completed successfully.")
        else:
            self.ai_status.setText("AI Status: Training Failed")
            QMessageBox.warning(self, "Training Failed", 
                              "AI training encountered an error.")

    def on_ai_action(self, action):
        """Handle AI actions for visualization"""
        tower_type, x, y = action
        tower_names = {1: "Basic", 2: "Bomb", 3: "Booster"}
        
        if tower_type > 0:
            self.ai_status.setText(f"AI Status: Placed {tower_names.get(tower_type, '')} Tower at ({x},{y})")
        else:
            self.ai_status.setText("AI Status: Evaluating...")
if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    
    app.exec()
