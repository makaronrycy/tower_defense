from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal,QObject,Slot
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QBrush, QColor, QPainterPath,QPen
from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QGraphicsView
from PySide6.QtCore import QEvent, QObject, Signal, Slot

from graphicItems import GhostTowerItem ,BaseItem, BaseTowerItem, RangeIndicator, ProjectileItem
from towers import BasicTower, BombTower, BoosterTower,BombProjectile, ExplosionProjectile,BasicProjectile
from enemies import Rat, FastRat, GiantRat

from animationManager import AsepriteLoader,SpriteSheet
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
        self._gold = 1000
        self._score = 0
        self._lives = 20
        self._level = 1
        self._wave = 1
        self._wave_started = False
        
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
        
        # Setup game systems
        self._init_path()
        self._setup_timers()
        self._prepare_animations()
        self._connect_signals()
        self._background = QBrush(QColor(50, 50, 50))
        self.setBackgroundBrush(self._background)
    # ----------------------
    # Initialization Methods
    # ----------------------
    def _prepare_animations(self):
        # Load animations here
        bomb_tower_animation = AsepriteLoader("spritesheets/bomb_tower.json")
        bomb_tower_spritesheet = SpriteSheet("spritesheets/bomb_tower.png")

        basic_tower_animation = AsepriteLoader("spritesheets/basic_tower.json")
        basic_tower_spritesheet = SpriteSheet("spritesheets/basic_tower.png")

        booster_tower_animation = AsepriteLoader("spritesheets/booster_tower.json")
        booster_tower_spritesheet = SpriteSheet("spritesheets/booster_tower.png")

        rat_animation = AsepriteLoader("spritesheets/rat.json")
        rat_spritesheet = SpriteSheet("spritesheets/rat.png")

        fast_rat_animation = AsepriteLoader("spritesheets/fast_rat.json")
        fast_rat_spritesheet = SpriteSheet("spritesheets/fast_rat.png")

        giant_rat_animation = AsepriteLoader("spritesheets/giant_rat.json")
        giant_rat_spritesheet = SpriteSheet("spritesheets/giant_rat.png")

        basic_projectile_animation = AsepriteLoader("spritesheets/basic_projectile.json")
        basic_projectile_spritesheet = SpriteSheet("spritesheets/basic_projectile.png")

        bomb_projectile_animation = AsepriteLoader("spritesheets/bomb_projectile.json")
        bomb_projectile_spritesheet = SpriteSheet("spritesheets/bomb_projectile.png")

        explosion_projectile_animation = AsepriteLoader("spritesheets/explosion_projectile.json")
        explosion_projectile_spritesheet = SpriteSheet("spritesheets/explosion_projectile.png")
        
        self.animations = {
            "bomb_tower":{
                "spritesheet" :bomb_tower_spritesheet,
                "anim_data": bomb_tower_animation.get_anim_data()
            }
            ,"basic_tower":{
                "spritesheet" :basic_tower_spritesheet,
                "anim_data": basic_tower_animation.get_anim_data()
            }
            ,"booster_tower":{
                "spritesheet" :booster_tower_spritesheet,
                "anim_data": booster_tower_animation.get_anim_data()
            }
            ,"rat":{
                "spritesheet" :rat_spritesheet,
                "anim_data": rat_animation.get_anim_data()
            }
            ,"fast_rat":{
                "spritesheet" :fast_rat_spritesheet,
                "anim_data": fast_rat_animation.get_anim_data()
            }
            ,"giant_rat":{
                "spritesheet" :giant_rat_spritesheet,
                "anim_data": giant_rat_animation.get_anim_data()
            }
            ,"basic_projectile":{
                "spritesheet" :basic_projectile_spritesheet,
                "anim_data": basic_projectile_animation.get_anim_data()
            }
            ,"bomb_projectile":{
                "spritesheet" :bomb_projectile_spritesheet,
                "anim_data": bomb_projectile_animation.get_anim_data()
            }
            ,"explosion_projectile":{
                "spritesheet" :explosion_projectile_spritesheet,
                "anim_data": explosion_projectile_animation.get_anim_data()
            }
        }
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
        self._repaint_scene()
        self.update_viewport(self.sceneRect())
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
                continue
            enemy.advance_animation(16)

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
                if isinstance(item, Rat):
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
            new_tower = BoosterTower(pos)
        self.game_items['towers'].append(new_tower)
        self.addItem(new_tower)
        

    def add_projectile(self, projectile):
        """Register new projectile"""
        self.game_items['projectiles'].append(projectile)
        self.addItem(projectile)

    def spawn_enemy(self):
        """Create and register new enemy"""
        enemy = Rat(path=self.path_points, animation=self.animations["rat"])
        #enemy = FastRat(path=self.path_points, animation=self.animations["fast_rat"])
        #enemy = GiantRat(path=self.path_points, animation=self.animations["giant_rat"])
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
            tower.upgrade()
        # Implement upgrade logic here
        pass
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
            if item.isVisible() and item.collidesWithItem(check_item) and not isinstance(item, RangeIndicator) and not isinstance(item, GhostTowerItem) and not isinstance(item, ProjectileItem):
                print(f"Collision with {item}")
                return False
        return True

    def _create_visual_path(self):
        """Generate visible path representation"""
        for i,point in enumerate(self.path_points[1:]):
            line = QPainterPath()
            line.moveTo(self.path_points[i])
            line.lineTo(point)
            self.addPath(line, QPen(Qt.darkGreen, 20))
