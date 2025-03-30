from PySide6.QtCore import Qt, QRectF, QPointF, Property, QObject, Signal, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject
from animationManager import SpriteSheet, AnimationComponent
from PySide6.QtGui import QPainter, QPainterPath, QColor, QBrush,QPixmap
from animationManager import AnimationComponent
from abc import ABC, abstractmethod
import math
class BaseItem(QGraphicsObject):
    def __init__(self,parent=None, animation = None):
        super().__init__(parent)
        self._health = 100
        self._z_value = 0
        self._collision_enabled = True
        
        # Setup common flags
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCacheMode(QGraphicsItem.NoCache)  # Sometimes better for animated items
        
        # Animation system
        if animation is None:
            animation = {
                #dummy data
                "spritesheet": SpriteSheet("path/to/spritesheet.png"),
                "anim_data": {
                    "idle": {
                        "from": 0,
                        "to": 4,
                        0: {"rect": QRectF(0, 0, 32, 32), "duration": 0.1},
                        1: {"rect": QRectF(32, 0, 32, 32), "duration": 0.1},
                    }
                }
            }
        else:
            self.animations = AnimationComponent(animation["spritesheet"],animation["anim_data"])
        self.current_frame = QPixmap()
        self.facing_right = True


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

    def advance_animation(self, interval) -> None:
        """Update animation based on delta time"""
        # Convert milliseconds to seconds for the animation component
        self.animations.update(interval / 1000.0)
        self.update()  # Request a repaint

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

    #helper functions
    def distance_between_points(self,point1,point2):
        return math.sqrt((point1.x()-point2.x())**2 + (point1.y()-point2.y())**2)
    def paint_sprite(self, painter: QPainter, pixmap: QPixmap) -> None:
        """Helper method to draw a sprite centered on the item's position"""
        # Calculate the top-left position to center the pixmap
        #possible scaling, but would have to change other graphic elements and maybe tileset functionality
        #painter.save()
    
        # Apply 2x scaling
        #painter.scale(2.0, 2.0)
        x = -pixmap.width() / 2
        y = -pixmap.height() / 2

        # Draw the pixmap centered
        painter.drawPixmap(QRectF(x, y, pixmap.width(), pixmap.height()), pixmap, pixmap.rect())
        #painter.restore()
class MapItem(QGraphicsItem):
    def __init__(self, pixmap):
        super().__init__()
        self._image :QPixmap = pixmap
        self.setZValue(-10)  # Below other items

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._image.width(), self._image.height())

    def paint(self, painter, option, widget):
        painter.drawPixmap(self._image.rect().topLeft(), self._image)
class ObstacleItem(QGraphicsItem):
    def __init__(self, pixmap):
        super().__init__()
        self._image = pixmap
        self.setZValue(-1)  # Below other items

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._image.width(), self._image.height())

    def paint(self, painter, option, widget):
        painter.drawPixmap(self._image.rect().topLeft(), self._image)
class PathItem(QGraphicsItem):
    def __init__(self, pixmap):
        super().__init__()
        self._image = pixmap
        self.setZValue(-1)  # Below other items

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._image.width(), self._image.height())

    def paint(self, painter, option, widget):
        painter.drawPixmap(self._image.rect().topLeft(), self._image)
        
        

class BaseTowerItem(BaseItem):
    kills_changed = Signal(int) # Emit when kills change
    def __init__(self,pos,animation = None):
        super().__init__(animation=animation)
        self.set_z_value(1)
        self.setPos(pos)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
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
        pixmap = self.animations.get_current_frame()
        width = pixmap.width()*2
        height = pixmap.height()*2
        # Center the rectangle around (0,0)
        return QRectF(-width/2, -height/2, width, height)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        pic = self.animations.get_current_frame()
        self.paint_sprite(painter, pic)
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
    
class BaseEnemyItem(BaseItem):
    def __init__(self,path,animation = None):
        super().__init__(animation=animation)
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
        pixmap = self.animations.get_current_frame()
        width = pixmap.width()
        height = pixmap.height()
        # Center the rectangle around (0,0)
        return QRectF(-width/2, -height/2, width, height)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        pic = self.animations.get_current_frame()
        self.paint_sprite(painter, pic)

    def update_direction(self, target_pos):
        """Flip sprite based on movement direction"""
        self.facing_right = target_pos.x() > self.x()
    def update(self) -> None:
        self.follow_path()


    def follow_path(self):
        # Define a minimum waypoint proximity threshold
        waypoint_threshold = max(5.0, self._speed)  # At least 5 pixels or the speed value
        
        # Check if we've reached the current waypoint or passed it
        distance_to_waypoint = self.distance_between_points(self.pos(), self._current_waypoint)
        
        if distance_to_waypoint < waypoint_threshold:
            # Get next waypoint if available
            current_index = self._path.index(self._current_waypoint)
            if current_index < len(self._path) - 1:
                # Move to next waypoint
                self._current_waypoint = self._path[current_index + 1]
                self.update_direction(self._current_waypoint)
        
        # Calculate direction vector to current waypoint
        direction = QPointF(
            self._current_waypoint.x() - self.pos().x(),
            self._current_waypoint.y() - self.pos().y()
        )
        
        # Normalize the direction vector
        length = math.sqrt(direction.x()**2 + direction.y()**2)
        if length > 0:
            normalized_dir = QPointF(direction.x() / length, direction.y() / length)
            
            # Scale by speed but prevent overshooting
            move_distance = min(self._speed, distance_to_waypoint)
            move_vector = QPointF(normalized_dir.x() * move_distance, normalized_dir.y() * move_distance)
            
            # Move along that direction
            self.setPos(self.pos() + move_vector)
        
        # Check for stuck condition (optional)
        # If an enemy hasn't made significant progress toward waypoint after several updates
        # we could add some recovery logic here

class ProjectileItem(BaseItem):
    def __init__(self,pos,target,parentTower,animation = None):
        super().__init__(animation=animation)
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
        pixmap = self.animations.get_current_frame()
        width = pixmap.width()
        height = pixmap.height()
        # Center the rectangle around (0,0)
        return QRectF(-width/2, -height/2, width, height)

    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        pic = self.animations.get_current_frame()
        self.paint_sprite(painter, pic)

    
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
class GhostTowerItem(QGraphicsItem):
    def __init__(self, tower_type):
        super().__init__()
        self.name = tower_type["type"]
        self.cost = tower_type["cost"]
        self.valid = False
        self._radius = 20
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