from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView,QLabel,QVBoxLayout,QWidget
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QPushButton, QGraphicsView

from PySide6.QtWidgets import QMainWindow,  QDialog, QFormLayout, QSpinBox, QCheckBox,QMessageBox
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtCore import Qt, QRectF, QTimer, QPoint, Signal,QObject
from PySide6.QtWidgets import QGraphicsView, QApplication
from PySide6.QtGui import QWheelEvent, QMouseEvent, QPainter, QTransform, QAction
from ui import GameView, TowerStoreWidget,TowerOverviewWidget,MultiplayerInfoWidget

from config_dialog import ConfigurationDialog
from graphicsScenes import GameScene, GameState


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
        dialog.exec()

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
                server_ip = config.get("server_ip", "127.000.000.001")
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
        

    def hide_uis(self):
        """Hide the UI elements when the game is over"""
        self.store.hide()
        self.tower_overview.hide()
        self.multiplayer_info.hide()
if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    
    app.exec()
