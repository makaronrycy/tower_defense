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
        self._health = 20
        self._target = None
        self._selected = False
        self.value = 20
    
    def update(self) -> None:
        self.follow_path()
class FastRat(BaseEnemyItem):
    def __init__(self,path):
        super().__init__(path=path)
        self.set_z_value(1)
        self.setPos(QPointF(0, 300))
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self._color = QColor(0, 255, 255, 255)
        self._radius = 20
        self._speed = 2
        self._health = 50
        self.value = 40

    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(0, 0, 0, 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "FastRat")
    
    def update(self) -> None:
        self.follow_path()
class GiantRat(BaseEnemyItem):
    def __init__(self,path):
        super().__init__(path=path)
        self.set_z_value(1)
        self.setPos(QPointF(0, 300))
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self._color = QColor(255, 0, 0, 255)
        self._radius = 30
        self._speed = 1
        self._health = 200
        self.value = 100

    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(0, 0, 0, 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "GiantRat")
    
    def update(self) -> None:
        self.follow_path()