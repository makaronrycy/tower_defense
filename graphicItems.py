from PySide6.QtCore import Qt, QRectF, QPointF, Property, QObject, Signal, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject
from PySide6.QtGui import QPainter, QPainterPath, QColor, QBrush

from abc import ABC, abstractmethod
import math
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
    
    

class BaseTowerItem(BaseItem):
    kills_changed = Signal(int) # Emit when kills change
    def __init__(self,pos):
        super().__init__()
        self.set_z_value(1)
        self.setPos(pos)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        self.cost = 0
        self._color = QColor(255, 0, 0, 255)
        self._radius = 25
        self._damage = 10
        self.range = 100
        self._fire_rate = 100
        self._target = None
        self._selected = False
        self._cooldown = 0
        self.kills = 0
        self.upgrade_cost = 20
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.scene().tower_selected.emit(self if value else None)  # Emit signal when tower is selected
        return super().itemChange(change, value)
    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(0, 0, 0, 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "Tower")
    def can_upgrade(self,gold):
        return True if gold >= self.upgrade_cost else False
    @abstractmethod
    def upgrade(self) -> None:
        """Must implement in subclasses"""
        pass
    def update(self) -> None:
        if self._cooldown > 0:
            self._cooldown -= 1

    def acquire_target(self, enemies):
        for enemy in enemies:
            if self.distance_between_points(self.pos(),enemy.pos()) < self.range:
                self._target = enemy
                return enemy
    def should_fire(self):
        return True if self._target and self._cooldown == 0 else False

    def add_kill(self):
        self.kills += 1
        self.kills_changed.emit(self)  # Emit signal when kills change
        print(f"Tower {self.name} has {self.kills} kills.")
        
    def hoverEnterEvent(self, event):
        return super().hoverEnterEvent(event)
    def distance_between_points(self,point1,point2):
        return math.sqrt((point1.x()-point2.x())**2 + (point1.y()-point2.y())**2)
class BasicTower(BaseTowerItem):
    def __init__(self,pos):
        super().__init__(pos=pos)
        self.set_z_value(1)
        self.setPos(pos)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self.name = "Basic Tower"
        self.cost = 30
        self._damage = 10
        self.range = 100
        self._fire_rate = 100
        self._cooldown = 0
        self.upgrade_cost = 20
    
    def upgrade(self):
        self._damage += 5
        self.range += 20
        self._fire_rate -= 10
        self.cost += 20
        print(f"Upgraded {self.name}: Damage: {self._damage}, Range: {self.range}, Fire Rate: {self._fire_rate}")
    def create_projectile(self,enemyPos):
        self._cooldown = self._fire_rate
        p = ProjectileItem(self.pos(),enemyPos,self)
        return p
class BombTower(BaseTowerItem):
    def __init__(self,pos):
        super().__init__(pos=pos)
        self.set_z_value(1)
        self.setPos(pos)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self.name = "Bomb Tower"
        self.cost = 50
        self._damage = 20
        self.range = 150
        self._fire_rate = 200
        self._cooldown = 0
        self.upgrade_cost = 30
    def create_projectile(self,enemyPos):
        self._cooldown = self._fire_rate
        p = BombProjectile(self.pos(),enemyPos,self)
        return p
class BoosterTower(BaseTowerItem):
    def __init__(self,pos):
        super().__init__(pos=pos)
        self.set_z_value(1)
        self.setPos(pos)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self.name = "Booster Tower"
        self.cost = 50
        self._damage = 0
        self.range = 150
        self._fire_rate = 200
        self._cooldown = 0
        self.upgrade_cost = 30
        self.boosted_towers = []
    def upgrade(self):
        self.range += 20

        
    def create_projectile(self,enemyPos):
        pass
    def boost_tower(self,tower):
        if tower not in self.boosted_towers:
            tower._damage += 5
            tower.range += 20
            tower._fire_rate -= 10
            self.boosted_towers.append(tower)
            print(f"Boosted {tower.name}: Damage: {tower._damage}, Range: {tower.range}, Fire Rate: {tower._fire_rate}")
    def unboost_tower(self,tower):
        if tower in self.boosted_towers:
            tower._damage -= 5
            tower.range -= 20
            tower._fire_rate += 10
            self.boosted_towers.remove(tower)
            print(f"Unboosted {tower.name}: Damage: {tower._damage}, Range: {tower.range}, Fire Rate: {tower._fire_rate}")
    
class BaseEnemyItem(BaseItem):
    def __init__(self,path):
        super().__init__()
        self.set_z_value(1)
        self.setPos(QPointF(0, 300))
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self._color = QColor(0, 255, 0, 255)
        self._radius = 20
        self._speed = 10
        self._health = 100
        self._path = path

        
        #path[0] to punkt startowy
        self._current_waypoint = path[1]
        self._target = None
        self._selected = False
        self.value = 20

    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(0, 0, 0, 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "Enemy")
    
    def update(self) -> None:
        self.follow_path()

    def follow_path(self):
        if(self.pos() == self._current_waypoint):
            self._current_waypoint = self._path[self._path.index(self._current_waypoint)+1]
        if(self.pos().x() < self._current_waypoint.x()):
            self.setPos(self.pos() + QPointF(self._speed, 0))
        elif(self.pos().x() > self._current_waypoint.x()):
            self.setPos(self.pos() - QPointF(self._speed, 0))
        elif(self.pos().y() < self._current_waypoint.y()):  
            self.setPos(self.pos() + QPointF(0, self._speed))
        elif(self.pos().y() > self._current_waypoint.y()):
            self.setPos(self.pos() - QPointF(0, self._speed))

class ProjectileItem(BaseItem):
    def __init__(self,pos,target,parentTower):
        super().__init__()
        self.set_z_value(1)
        self.setPos(pos)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self._color = QColor(0, 0, 255, 255)
        self._radius = 5
        self._speed = 10
        self._damage= 100
        self._pierce = 0
        self.parentTower = parentTower
        self._direction = target - pos if target != None else QPointF(0, 0)
        # Normalize the direction vector
        direction_length = math.sqrt(self._direction.x()**2 + self._direction.y()**2)
        if direction_length != 0:
            self._direction /= direction_length
        self._selected = False
        self._lifetime = 1000

    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(0, 0, 0, 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "Bullet")
    
    def update(self) -> None:
        self.update_position()
        self.is_expired()
    def update_position(self):
        self.setPos(self.pos() + self._direction * self._speed)
        self._lifetime -= 1
        pass
    def is_expired(self):
        if self._lifetime <= 0 or self._pierce < 0:
            return True
        return False
class BombProjectile(ProjectileItem):
    def __init__(self,pos,target,parentTower):
        super().__init__(pos=pos,target=target,parentTower=parentTower)
        self._color = QColor(255, 0, 0, 255)
        self._radius = 10
        self._damage= 200
        self._lifetime = 1000
    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(255, 0,0 , 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "Bomb")
class ExplosionProjectile(ProjectileItem):
    def __init__(self,pos,target,parentTower):
        super().__init__(pos=pos,target=target,parentTower=parentTower)

        self._speed = 0
        self._damage = 20
        self._pierce = 999
        self._color = QColor(255, 255, 0, 255)
        self._radius = 50
        self._lifetime = 100  # Duration of the explosion effect
    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(255, 0,0 , 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "Explosion")
class GhostTowerItem(QGraphicsItem):
    def __init__(self, tower_type):
        super().__init__()
        self.name = tower_type["type"]
        self.cost = tower_type["cost"]
        self.valid = False
        self._radius = 30
        self.setOpacity(0.5)
        self.setZValue(100)  # Above other items

    def paint(self, painter, option, widget):
        # Draw semi-transparent tower
        painter.setBrush(QColor(255, 255, 255, 128))
        painter.drawRect(self.boundingRect())
        
        # Draw validity indicator
        if self.valid:
            painter.setBrush(Qt.green)
        else:
            painter.setBrush(Qt.red)
        painter.drawEllipse(self.boundingRect())
    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
class Rat(BaseEnemyItem):
    def __init__(self,path):
        super().__init__(path=path)
        self.set_z_value(1)
        self.setPos(QPointF(0, 300))
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        self._color = QColor(0, 255, 0, 255)
        self._radius = 20
        self._speed = 1
        self._health = 100
        self._target = None
        self._selected = False
        self.value = 20

    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QColor(0, 0, 0, 255))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, "Rat")
    
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
class RangeIndicator(QGraphicsItem):
    def __init__(self, tower: BaseTowerItem):
        super().__init__()
        self._tower = tower
        self.setPos(tower.pos())
        self.setZValue(-1)  # Above other items

    def boundingRect(self) -> QRectF:
        return QRectF(-self._tower.range, -self._tower.range, self._tower.range * 2, self._tower.range * 2)

    def paint(self, painter, option, widget):
        painter.setPen(QColor(0, 0, 255, 128))  # Semi-transparent blue
        painter.drawEllipse(self.boundingRect())