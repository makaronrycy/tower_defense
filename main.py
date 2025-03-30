from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView,QLabel,QVBoxLayout,QWidget
from graphicItems import BaseItem
from PySide6.QtGui import QColor
from graphicsScenes import GameScene, GameState

from PySide6.QtCore import Qt, QRectF, QTimer, QPoint, Signal,QObject
from PySide6.QtWidgets import QGraphicsView, QApplication
from PySide6.QtGui import QWheelEvent, QMouseEvent, QPainter, QTransform
from ui import GameView, TowerStoreWidget,TowerOverviewWidget
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QPushButton, QGraphicsView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tower Defense")
        self.scene = GameScene()
        self.view = GameView(self.scene)
        self.store = TowerStoreWidget(self.scene.game_state)
        self.tower_overview =TowerOverviewWidget(self.scene.game_state)
        
        splitter = QSplitter()
        splitter.addWidget(self.tower_overview)
        splitter.addWidget(self.view)
        splitter.addWidget(self.store)
        self.setCentralWidget(splitter)

        
        self.store.update_store_ui(self.scene.game_state.gold)
        #connections
        
        self.scene.game_state.gold_changed.connect(self.store.update_store_ui)
        self.scene.game_state.gold_changed.connect(self.tower_overview.update_upgrade_ui)

        self.scene.game_state.lives_changed.connect(self.store.update_lives_ui)
        self.scene.tower_selected.connect(self.tower_overview.update_overview_ui)

        self.scene.repaint_view.connect(self.view.repaint_view)

        self.store.tower_selected.connect(self.scene.start_tower_placement)
        self.tower_overview.tower.kills_changed.connect(self.tower_overview.update_overview_ui)
        
        self.tower_overview.sell_tower.connect(self.scene.handle_tower_sale)
        self.tower_overview.upgrade_tower.connect(self.scene.handle_tower_upgrade)
        self.tower_overview.tower_deselected.connect(self.scene.handle_tower_deselection)
        self.scene.tower_selected.connect(self.scene.handle_tower_selection)

        self.store.wave_started.connect(self.scene.start_wave)
        self.scene.game_over_signal.connect(self.store.handle_game_over)
        self.scene.wave_ended.connect(self.store.handle_wave_end)
        QTimer.singleShot(1000, self.scene.start_game)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    
    app.exec()
