from PySide6.QtCore import Qt, QRectF, QPointF, Property, QObject, Signal, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject
from PySide6.QtGui import QPainter, QPainterPath, QColor, QBrush

from abc import ABC, abstractmethod
class BaseItem(QGraphicsObject):
    def __init__(self,parent=None):
        super().__init__(parent)
        self._health = 100
        self._z_value = 0
        self._collision_enabled = True
        
        # Setup common flags
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        
        # Animation system
        self._animations = {}
        if self.__class__ is BaseItem:
            raise TypeError("Cannot instantiate abstract BaseItem")
    @abstractmethod
    def boundingRect(self) -> QRectF:
        """Must implement in subclasses"""
        return QRectF()

    @abstractmethod
    def paint(self, painter: QPainter, option, widget=None) -> None:
        """Must implement in subclasses"""
        pass

    @abstractmethod
    def update(self) -> None:
        """Custom update mechanism for game logic"""
        super().update()

    # =====================
    # Common functionality
    # =====================
    def shape(self) -> QPainterPath:
        """Default collision shape (circle)"""
        path = QPainterPath()
        path.addEllipse(self.boundingRect())
        return path

    def set_z_value(self, value: int) -> None:
        """Layer management
        0 - background
        1 - enemies and towers
        2 - projectiles
        3 - effects
        4 - UI
        """
        self._z_value = value
        self.setZValue(value)

    def advance(self, phase: int) -> None:
        """Game loop updates"""
        if phase == 1:  # Only process during second phase
            self.update()

    # =====================
    # Animation system
    # =====================
    def add_animation(self, name: str, target: QObject, property_name: bytes):
        """Register animation properties"""
        anim = QPropertyAnimation(target, property_name, self)
        self._animations[name] = anim
        anim.valueChanged.connect(self._on_animation_update)

    def _on_animation_update(self):
        """Trigger repaint on animation updates"""
        self.update()

    def start_animation(self, name: str, duration: int, start, end):
        """Start registered animation"""
        if name in self._animations:
            anim = self._animations[name]
            anim.setDuration(duration)
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.start()

    # =====================
    # Property definitions
    # =====================
    @Property(int)
    def health(self) -> int:
        return self._health

    @health.setter
    def health(self, value: int) -> None:
        self._health = max(0, min(100, value))
        self.update()

    @Property(float)
    def rotation_angle(self) -> float:
        return self.rotation()

    @rotation_angle.setter
    def rotation_angle(self, angle: float) -> None:
        self.setRotation(angle)

class TowerItem(BaseItem):
    def __init__(self):
        super().__init__()
        self.set_z_value(1)
        self.setPos(QPointF(400, 300))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self._color = QColor(255, 0, 0, 255)
        self._radius = 50
        self._damage = 10
        self._range = 200
        self._fire_rate = 1000
        self._last_fire = 0
        self._target = None
        self._projectiles = []
        self._selected = False

    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(0, 0, 0, 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "Tower")
    
    def update(self) -> None:
        pass
class EnemyItem(BaseItem):
    def __init__(self):
        super().__init__()
        self.set_z_value(1)
        self.setPos(QPointF(0, 300))
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self._color = QColor(0, 255, 0, 255)
        self._radius = 20
        self._speed = 1
        self._health = 100
        self._path = []
        self._waypoint = 0
        self._target = None
        self._selected = False

    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(0, 0, 0, 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "Enemy")
    
    def update(self) -> None:
        pass