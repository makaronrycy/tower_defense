from PySide6.QtCore import QRectF, QPointF, Qt, QLineF, QTimer, QObject, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsScene, QGraphicsView
from graphicItems import BaseEnemyItem
class Rat(BaseEnemyItem):
    def __init__(self,path,animation = None):
        super().__init__(path=path,animation=animation)
        self.set_z_value(1)
        self.setPos(QPointF(0, 300))
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        self._color = QColor(0, 255, 0, 255)
        self._radius = 20
        self._speed = 0.5
        self._health = 40
        self._target = None
        self._selected = False
        self.value = 20

class FastRat(BaseEnemyItem):
    def __init__(self,path,animation = None):
        super().__init__(path=path,animation=animation)
        self.set_z_value(1)
        self.setPos(QPointF(0, 300))
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self._color = QColor(0, 255, 255, 255)
        self._radius = 20
        self._speed = 1.5
        self._health = 20
        self.value = 40


class GiantRat(BaseEnemyItem):
    def __init__(self,path,animation = None):
        super().__init__(path=path,animation=animation)
        self.set_z_value(1)
        self.setPos(QPointF(0, 300))
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self._color = QColor(255, 0, 0, 255)
        self._radius = 30
        self._speed = 0.25
        self._health = 200
        self.value = 100