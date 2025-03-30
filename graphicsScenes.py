from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal,QObject,Slot
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QBrush, QColor, QPainterPath,QPen
from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QGraphicsView
from PySide6.QtCore import QEvent, QObject, Signal, Slot
from graphicItems import GhostTowerItem ,BaseItem, BaseTowerItem, RangeIndicator, ProjectileItem
from graphicItems import  PathItem, ObstacleItem, MapItem
from towers import BasicTower, BombTower, BoosterTower,BombProjectile, ExplosionProjectile,BasicProjectile
from enemies import Rat, FastRat, GiantRat
from map_generator import MapGenerator,MapGraphicsManager
from animationManager import AsepriteLoader,SpriteSheet, get_all_animations
from tileset import get_tileset
from waves import ENEMY_LIST, build_new_wave
import random
import config as cfg
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
        self._gold = cfg.BASE_GOLD
        self._score = 0
        self._lives = cfg.BASE_LIVES
        self._level = 1
        self.wave = 1
        self.wave_started = False
        self.enemies_to_spawn = []
        
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
    tower_selected = Signal(object)
    score_changed = Signal(int)
    lives_changed = Signal(int)
    repaint_view = Signal()
    wave_ended = Signal()
    game_over_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.game_active = False
        self.game_state = GameState()
        self.last_frame_time = 0.0
        # Game state containers
        self.game_items = {
            "towers": [],
            "enemies": [],
            "projectiles": []
        }
        self.current_range_indicator = None
        self.animations = get_all_animations()
        self.tileset = get_tileset()
        # Setup game systems
        self.path_points = []
        self._setup_timers()
        self._map_init()
        self._connect_signals()
        self._background = QBrush(QColor(50, 50, 50))
        self.setBackgroundBrush(self._background)
        
    # ----------------------
    # Initialization Methods
    # ----------------------
    def _map_init(self,height=cfg.MAP_HEIGHT,width=cfg.MAP_WIDTH):
        """Initialize grid and path system"""
        self.map_generator = MapGenerator(height,width)
        self.map_graphics_manager = MapGraphicsManager(self.map_generator.grid, 16, self.tileset)
        for item in self.map_graphics_manager.create_items():
            self.addItem(item)
        #self._init_grid()
        for p in self.map_generator.path:
            self.path_points.append(self.grid_to_scene(p))


    def _init_grid(self):
        """Create visual/logical grid system"""
        self.grid = {}
        cell_size = 16  # Pixels per grid cell
        for x in range(0, 800, cell_size):
            for y in range(0, 600, cell_size):
                rect = QRectF(x, y, cell_size, cell_size)
                self.grid[(x, y)] = rect
                # Draw grid cells (optional for debugging)
                # path = QPainterPath()
                # path.addRect(rect)
                # self.addPath(path, QPen(QColor(100, 100, 100, 50), 1))
    def grid_to_scene(self, grid_pos):
        """Convert grid coordinates to scene coordinates"""
        return QPointF(grid_pos[0] * 16, grid_pos[1] * 16)
    def scene_to_grid(self, scene_pos):
        """Convert scene coordinates to grid coordinates"""
        x = int(scene_pos.x() // 16) * 16
        y = int(scene_pos.y() // 16) * 16
        return (x, y)

    def game_over(self):
        """Handle game over state"""

        self.game_timer.stop()
        self.spawn_timer.stop()
        self.game_active = False
        self.game_over_signal.emit()
        # Show game over screen or reset game
        print("Game Over!")
        # Reset game state
    def _setup_timers(self):
        """Initialize game timers"""
        self.game_timer = QTimer()
        self.game_timer.setInterval(16)  # ~60 FPS
        self.game_timer.timeout.connect(self.advance)
        self.spawn_timer = QTimer()
        self.spawn_timer.setInterval(1000)
        self.spawn_timer.timeout.connect(self.spawn_enemy)
        
    def start_wave(self):
        """Start a new wave of enemies"""
        enemies = {}
        self.game_state.wave_started = True
        if self.game_state.wave > len(ENEMY_LIST):
            enemies = build_new_wave(self.game_state.wave)
        else:
            enemies = ENEMY_LIST[self.game_state.wave-1]
        enemy_type = ["rat", "FAST_RAT", "GIANT_RAT"]
        for enemy_type in enemies:
            enemies_to_spawn = enemies[enemy_type]
            for enemy in range(enemies_to_spawn):
                self.game_state.enemies_to_spawn.append(enemy_type)
        random.shuffle(self.game_state.enemies_to_spawn)
        self.spawn_timer.start()
    def end_wave(self):
        """End the current wave of enemies"""
        self.game_state.wave_started = False
        self.game_state.wave += 1
        self.wave_ended.emit()

    def _repaint_scene(self):
        """Repaint the scene to update visuals"""
        self.repaint_view.emit()
        
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

    def advance(self):
        """Main game update cycle"""
        if not self.game_active:
            return
        
        self._update_enemies()
        self._update_towers()
        self._update_projectiles()
        self._check_collisions()
        self._cleanup_items()
        #self._repaint_scene()
        #self.update_viewport(self.sceneRect())
    def update_viewport(self,viewport_rect: QRectF):
        """Update scene viewport"""
        for item in self.items():
            item_rect = item.mapRectToScene(item.boundingRect())

            if viewport_rect.intersects(item_rect):
                item.setVisible(True)
            else:
                item.setVisible(False)
        self.update(viewport_rect)

    # ----------------------
    # Update Subsystems
    # ----------------------
    def _cleanup_items(self):
        pass
    def _update_enemies(self):
        """Process enemy movement and health"""
        for enemy in self.game_items['enemies']:
            if enemy.health <= 0:
                self.game_state.score += enemy.value
                self.game_state.gold += enemy.value
                self.removeItem(enemy)
                self.game_items['enemies'].remove(enemy)

                continue
            if enemy.pos() == self.path_points[-1]:
                self.game_state.lives -= 1
                self.removeItem(enemy)
                self.game_items['enemies'].remove(enemy)
                if self.game_state.lives <= 0:

                    self.game_over()
                continue

            enemy.advance_animation(16)
        if self.game_items['enemies'] == [] and self.game_state.enemies_to_spawn == [] and self.game_state.wave_started:
            self.end_wave()

    def _update_towers(self):
        """Handle tower targeting and shooting"""
        for tower in self.game_items['towers']:
            enemy = tower.acquire_target(self.game_items['enemies'])
            
            if tower.should_fire() and enemy is not None:
                
                tower.set_cooldown()
                if isinstance(tower, BasicTower):
                    projectile = BasicProjectile(tower.pos(), enemy.pos(), tower,self.animations["basic_projectile"])
                    self.add_projectile(projectile)
                if isinstance(tower, BombTower):
                    projectile = BombProjectile(tower.pos(), enemy.pos(), tower, self.animations["bomb_projectile"])
                    self.add_projectile(projectile)
                
            tower.advance_animation(16)
    def _handle_projectile_hit(self, projectile, enemy):
        """Process projectile-enemy collision"""
        
        enemy._health -= projectile._damage
        projectile._pierce -= 1
        if enemy._health <= 0:
            projectile.parentTower.add_kill()
    def _handle_projectile_death(self, projectile):
        """Process projectile expiration"""
        if isinstance(projectile, BombProjectile):
            explosion = ExplosionProjectile(projectile.pos(),None,projectile.parentTower,self.animations["explosion_projectile"])
            self.add_projectile(explosion)
            
        self.removeItem(projectile)
        self.game_items['projectiles'].remove(projectile)
    def _update_projectiles(self):
        """Move projectiles and check lifespan"""
        for projectile in self.game_items['projectiles']:
            projectile.advance_animation(8)
            if projectile.is_expired():
                self._handle_projectile_death(projectile)
            
            

    # ----------------------
    # Collision Detection
    # ----------------------
    def _check_collisions(self):
        """Detect and handle collisions"""
        for projectile in self.game_items['projectiles']:
            colliding = self.collidingItems(projectile)
            for item in colliding:
                if isinstance(item, Rat) or isinstance(item, FastRat) or isinstance(item, GiantRat):
                    print(f"{projectile.__class__.__name__} hit {item.__class__.__name__}: {item._health} health left")
                    self._handle_projectile_hit(projectile, item)

    # ----------------------
    # Item Management
    # ----------------------
    def add_tower(self, tower, pos):
        """Register new tower"""
        new_tower = None
        if(tower.name == "basic"):
            new_tower = BasicTower(pos,self.animations["basic_tower"])
        
        elif(tower.name == "bomb"):
            new_tower = BombTower(pos,self.animations["bomb_tower"])
        elif(tower.name == "booster"):
            new_tower = BoosterTower(pos,self.animations["booster_tower"])
            #boost towers around it
            self.boost_around_tower(new_tower)
        self.game_items['towers'].append(new_tower)
        self.addItem(new_tower)
        
    def boost_around_tower(self,tower):
        """Boost towers around the tower"""
        for item in self.items():
            if isinstance(item, BaseTowerItem) and item != tower:
                if tower.collidesWithItem(item):
                    tower.boost_tower(item)
    def add_projectile(self, projectile):
        """Register new projectile"""
        self.game_items['projectiles'].append(projectile)
        self.addItem(projectile)

    def spawn_enemy(self):
        """Create and register new enemy"""
        enemy = None
        if not self.game_state.enemies_to_spawn:
            self.spawn_timer.stop()
        if self.game_state.enemies_to_spawn[0] == "rat":
            enemy = Rat(path=self.path_points, animation=self.animations["rat"])
        if self.game_state.enemies_to_spawn[0] == "fast_rat":
            enemy = FastRat(path=self.path_points, animation=self.animations["fast_rat"])
        if self.game_state.enemies_to_spawn[0] == "giant_rat":
            enemy = GiantRat(path=self.path_points, animation=self.animations["giant_rat"])
        if enemy:
            self.game_state.enemies_to_spawn.pop(0)
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
    @Slot(object)
    def handle_tower_upgrade(self, tower):
        """Handle tower upgrade"""
        if self.game_state.gold >= tower.upgrade_cost:
            self.game_state.gold -= tower.upgrade_cost
            # Pass any value - it's not used but required for the setter
            tower.upgrade_level = 0  # The actual value doesn't matter
            tower.upgrade()  # Call the tower's upgrade method to update stats
    @Slot(object)
    def handle_tower_selection(self, tower):
        """Display tower range"""
        if self.current_range_indicator:
            self.removeItem(self.current_range_indicator)
        if tower:
            self.current_range_indicator = RangeIndicator(tower)
            self.addItem(self.current_range_indicator)
    @Slot(object)
    def handle_tower_deselection(self):
        """Remove tower range display"""
        if self.current_range_indicator:
            self.removeItem(self.current_range_indicator)
            self.current_range_indicator = None

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
            if item.isVisible() and item.collidesWithItem(check_item) and (isinstance(item, PathItem) or isinstance(item, ObstacleItem) or  isinstance(item, BaseTowerItem)):
                print(f"Collision with {item}")
                return False
        return True
