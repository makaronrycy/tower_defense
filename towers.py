from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView
from PySide6.QtCore import QRectF, QPointF, Qt, QTimer
from graphicItems import BaseTowerItem, ProjectileItem
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPixmap
from animationManager import AnimationComponent

class BasicProjectile(ProjectileItem):
    def __init__(self,pos,target,parentTower,animation = None):
        super().__init__(pos=pos,target=target,parentTower=parentTower,animation=animation)
        self._color = QColor(0, 255, 0, 255)
        self._radius = 5
        self._damage= 10
        self._lifetime = 1000

class BombProjectile(ProjectileItem):
    def __init__(self,pos,target,parentTower,animation = None):
        super().__init__(pos=pos,target=target,parentTower=parentTower,animation=animation)
        self._color = QColor(255, 0, 0, 255)
        self._radius = 10
        self._damage= 200
        self._lifetime = 1000

class ExplosionProjectile(ProjectileItem):
    def __init__(self,pos,target,parentTower,animation = None):
        super().__init__(pos=pos,target=target,parentTower=parentTower,animation=animation)

        self._speed = 0
        self._damage = 20
        self._pierce = 999
        self._color = QColor(255, 255, 0, 255)
        self._radius = 50
        self._lifetime = 100  # Duration of the explosion effect

class BasicTower(BaseTowerItem):
    def __init__(self,pos,animation = None):
        super().__init__(pos=pos,animation=animation)
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
    def set_cooldown(self):
        self._cooldown = self._fire_rate

class BombTower(BaseTowerItem):
    def __init__(self,pos,animation = None):
        super().__init__(pos=pos,animation=animation,max_upgrade_level=2)
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
    def upgrade(self):
        self._damage += 10
        self.range += 30
        self._fire_rate -= 20
        self.cost += 30
        print(f"Upgraded {self.name}: Damage: {self._damage}, Range: {self.range}, Fire Rate: {self._fire_rate}")
    def set_cooldown(self):
        self._cooldown = self._fire_rate
class BoosterTower(BaseTowerItem):
    def __init__(self,pos,animation = None):
        super().__init__(pos=pos,animation=animation)
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
        self.boost_value = 1.5
        self.boosted_towers = []
    def upgrade(self):
        self.upgrade_cost += 20
        self.upgrade_level += 1
        self.range += 20
        self._fire_rate -= 10
        self.cost += 20
        
    def create_projectile(self,enemyPos):
        pass
    def set_cooldown(self):
        pass
    def boost_tower(self,tower:BaseTowerItem):
        if tower not in self.boosted_towers:
            tower.boost_modifier = self.boost_value
            self.boosted_towers.append(tower)
            print(f"Boosted {tower.name}: Damage: {tower._damage}, Range: {tower.range}, Fire Rate: {tower._fire_rate}")
    def unboost_tower(self,tower):
        if tower in self.boosted_towers:
            tower.boost_modifier = 1.0
            self.boosted_towers.remove(tower)
            print(f"Unboosted {tower.name}: Damage: {tower._damage}, Range: {tower.range}, Fire Rate: {tower._fire_rate}")
    
