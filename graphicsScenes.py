from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal,QObject,Slot
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QBrush, QColor, QPainterPath,QPen
from graphicItems import BasicTower, Rat, ProjectileItem,GhostTowerItem
from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QGraphicsView
from PySide6.QtCore import QEvent, QObject, Signal, Slot
'''
Klasa odpowiedzialna za sterowanie grą i jej elementami
'''
class GameState(QObject):
    gold_changed = Signal(int)
    score_changed = Signal(int)
    lives_changed = Signal(int)
    level_changed = Signal(int)
    def __init__(self):
        super().__init__()
        self._gold = 100
        self._score = 0
        self._lives = 20
        self._level = 1
        
    @property
    def gold(self):
        return self._gold
        
    @gold.setter
    def gold(self, value):
        self._gold = value
        self.gold_changed.emit(value)
    
    @property
    def score(self):
        return self._score
    
    @score.setter
    def score(self, value):
        self._score = value
        self.score_changed.emit(value)
    @property
    def lives(self):
        return self._lives
    
    @lives.setter
    def lives(self, value):
        self._lives = value
        self.lives_changed.emit(value)
    @property
    def level(self):
        return self._level
    @level.setter
    def level(self, value):
        self._level = value
        self.level_changed.emit(value)


class GameScene(QGraphicsScene):
    # Custom signals
    score_changed = Signal(int)
    lives_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.game_active = False
        self.game_state = GameState()
        
        # Game state containers
        self.game_items = {
            "towers": [],
            "enemies": [],
            "projectiles": []
        }

        
        # Setup game systems
        self._init_path()
        self._setup_timers()
        self._connect_signals()

    # ----------------------
    # Initialization Methods
    # ----------------------
    def _init_grid(self):
        """Create visual/logical grid system"""
        self.grid = {}
        cell_size = 40  # Pixels per grid cell
        for x in range(0, 800, cell_size):
            for y in range(0, 600, cell_size):
                self.grid[(x//cell_size, y//cell_size)] = {
                    'occupied': False,
                    'walkable': True
                }

    def _init_path(self):
        """Create enemy path with waypoints"""
        self.path_points = [
            QPointF(0, 300),
            QPointF(400, 300),
            QPointF(400, 100),
            QPointF(800, 100)
        ]
        self._create_visual_path()

    def _setup_timers(self):
        """Initialize game timers"""
        self.game_timer = QTimer()
        self.game_timer.setInterval(16)  # ~60 FPS
        self.game_timer.timeout.connect(self.advance)

        self.spawn_timer = QTimer()
        self.spawn_timer.setInterval(2000)
        self.spawn_timer.timeout.connect(self.spawn_enemy)

    def _connect_signals(self):
        """Connect internal signals"""
        #self.selectionChanged.connect(self._handle_selection_change)

    # ----------------------
    # Core Game Loop Methods
    # ----------------------
    def start_game(self):
        """Begin game progression"""
        self.game_active = True
        self.game_timer.start()
        self.spawn_timer.start()

    def advance(self):
        """Main game update cycle"""
        if not self.game_active:
            return

        self._update_enemies()
        self._update_towers()
        self._update_projectiles()
        self._check_collisions()
        self._cleanup_items()
    def update_viewport(self,viewport_rect: QRectF):
        """Update scene viewport"""
        for item in self.items():
            if item.isVisible():
                item.setVisible(viewport_rect.intersects(item.shape()))

    # ----------------------
    # Update Subsystems
    # ----------------------
    def _cleanup_items(self):
        pass
    def _update_enemies(self):
        """Process enemy movement and health"""
        for enemy in self.game_items['enemies']:
            if enemy.health == 0:
                self.game_state.score += enemy.value
                self.game_state.gold += enemy.value
                self.removeItem(enemy)
                self.game_items['enemies'].remove(enemy)
                continue
            if enemy.pos() == self.path_points[-1]:
                self.game_state.lives -= 1
                self.removeItem(enemy)
                self.game_items['enemies'].remove(enemy)
                continue
            enemy.update()

    def _update_towers(self):
        """Handle tower targeting and shooting"""
        for tower in self.game_items['towers']:
            enemy = tower.acquire_target(self.game_items['enemies'])
            if tower.should_fire() and enemy is not None:
                projectile = tower.create_projectile(enemy.pos())
                self.add_projectile(projectile)
            tower.update()
    def _handle_projectile_hit(self, projectile : ProjectileItem, enemy):
        """Process projectile-enemy collision"""
        enemy._health -= projectile._damage
        projectile.parentTower.add_kill()
        self.removeItem(projectile)
        self.game_items['projectiles'].remove(projectile)
    def _update_projectiles(self):
        """Move projectiles and check lifespan"""
        for projectile in self.game_items['projectiles']:
            projectile.update_position()
            if projectile.is_expired():
                self.removeItem(projectile)
                self.game_items['projectiles'].remove(projectile)

    # ----------------------
    # Collision Detection
    # ----------------------
    def _check_collisions(self):
        """Detect and handle collisions"""
        for projectile in self.game_items['projectiles']:
            colliding = self.items(projectile.pos())
            for item in colliding:
                
                if isinstance(item, Rat):
                    self._handle_projectile_hit(projectile, item)

    # ----------------------
    # Item Management
    # ----------------------
    def add_tower(self, tower, pos):
        """Register new tower"""
        new_tower = None
        if(tower.name == "basic"):
            new_tower = BasicTower(pos)
        
        elif(tower.name == "sniper"):
            new_tower = BasicTower(pos)
        self.game_items['towers'].append(new_tower)
        self.addItem(new_tower)

    def add_projectile(self, projectile):
        """Register new projectile"""
        self.game_items['projectiles'].append(projectile)
        self.addItem(projectile)

    def spawn_enemy(self):
        """Create and register new enemy"""
        enemy = Rat(path=self.path_points)
        self.game_items['enemies'].append(enemy)
        self.addItem(enemy)
        enemy.setPos(self.path_points[0])

    # ----------------------
    # User Interaction
    # ----------------------
    @Slot(dict)
    def start_tower_placement(self, tower_type):
        self.placement_ghost = GhostTowerItem(tower_type)
        self.addItem(self.placement_ghost)
        self.installEventFilter(self)
    @Slot(object)
    def handle_tower_sale(self, tower):
        """Handle tower sale"""
        self.removeItem(tower)
        self.game_items['towers'].remove(tower)
        self.game_state.gold += tower.cost // 2
    def handle_tower_upgrade(self, tower):
        """Handle tower upgrade"""
        # Implement upgrade logic here
        pass


    def eventFilter(self, source, event):
        if event.type() == QEvent.GraphicsSceneMouseMove:
            #Check if in valid position
            if self.is_valid_position(self.placement_ghost):
                print("Valid position")
                self.placement_ghost.valid = True
            else:
                print("Invalid position")
                self.placement_ghost.valid = False
            self.placement_ghost.setPos(event.scenePos())
        elif event.type() == QEvent.GraphicsSceneMousePress:
            if self.placement_ghost.valid:
                self.finalize_placement(event.scenePos())
        return super().eventFilter(source, event)

    def finalize_placement(self, pos):
        if self.is_valid_position(self.placement_ghost):
            self.add_tower(self.placement_ghost, pos)
            self.game_state.gold -= self.placement_ghost.cost
        self.cleanup_placement()

    def cleanup_placement(self):
        print("Cleaning up placement")
        self.removeItem(self.placement_ghost)
        self.placement_ghost = None
        self.removeEventFilter(self)


    # ----------------------
    # Helper Methods
    # ----------------------

    def is_valid_position(self,check_item):
        """Check if shape intersects with other item shapes"""
        for item in self.items():
            if item.isVisible() and item.collidesWithItem(check_item) and item != check_item:
                print(f"Collision with {item}")
                return False
        return True

    def _create_visual_path(self):
        """Generate visible path representation"""
        path = QPainterPath()
        
        path.moveTo(self.path_points[0])
        for point in self.path_points[1:]:
            path.lineTo(point)
        self.addPath(path, QPen(Qt.darkGreen, 20))
