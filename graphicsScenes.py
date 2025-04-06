from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal,QObject,Slot
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QBrush, QColor, QPainterPath,QPen
from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QGraphicsView,QGraphicsPathItem
from PySide6.QtCore import QEvent, QObject, Signal, Slot
from graphicItems import GhostTowerItem ,BaseItem, BaseTowerItem, RangeIndicator, ProjectileItem,BaseEnemyItem
from graphicItems import  PathItem, ObstacleItem, MapItem
from towers import BasicTower, BombTower, BoosterTower,BombProjectile, ExplosionProjectile,BasicProjectile
from enemies import Rat, FastRat, GiantRat
from map_generator import MapGenerator,MapGraphicsManager
from animationManager import AsepriteLoader,SpriteSheet, get_all_animations
from tileset import get_tileset
from waves import ENEMY_LIST, build_new_wave
import random
import config as cfg
from history_recorder import GameHistoryRecorder
from network import NetworkManager,GameNetworkEvent
'''
Klasa odpowiedzialna za sterowanie grą i jej elementami
'''
class GameState(QObject):
    gold_changed = Signal(int)
    score_changed = Signal(int)
    lives_changed = Signal(int)
    level_changed = Signal(int)
    record_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self._gold = cfg.BASE_GOLD
        self._score = 0
        self._lives = cfg.BASE_LIVES
        self._level = 1
        self.wave = 1
        self.wave_started = False
        self.enemies_to_spawn = []
        self._record = True
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
    @property
    def record(self):
        return self._record
    @record.setter
    def record(self, value):
        self._record = value
        self.record_changed.emit(value)


class GameScene(QGraphicsScene):
    # Custom signals
    tower_selected = Signal(object)
    score_changed = Signal(int)
    lives_changed = Signal(int)
    repaint_view = Signal()
    wave_ended = Signal()
    game_over_signal = Signal()
    network_event = Signal(dict)
    player_joined = Signal(str)
    player_left = Signal(str)
    def __init__(self, parent=None,multiplayer=False,is_host=False,map_gen = None):
        super().__init__(parent)

        self.game_active = False
        self.game_state = GameState()
        self.last_frame_time = 0.0

        self.multiplayer = multiplayer
        self.is_host = is_host

        self.player_id = None
        self.player_side = "left"

        if self.multiplayer:
            self.network = NetworkManager(is_host)
            self.network.connected.connect(self._on_network_connected)
            self.network.disconnected.connect(self._on_network_disconnected)
            self.network.event_received.connect(self._on_network_event)
            self.network.player_joined.connect(self._on_player_joined)
            self.network.player_left.connect(self._on_player_left)
            self.network.error.connect(self._on_network_error)
        self.map_divider = None
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
        self.history_recorder = GameHistoryRecorder()
        self._setup_timers()
        self._map_init(map_gen=map_gen)
        self._connect_signals()
        self._background = QBrush(QColor(50, 50, 50))
        self.setBackgroundBrush(self._background)
        
    # ----------------------
    # Initialization Methods
    # ----------------------
    def _map_init(self,height=cfg.MAP_HEIGHT,width=cfg.MAP_WIDTH,map_gen = None):
        if map_gen is None:
            """Initialize grid and path system"""
            self.map_generator = MapGenerator(height,width)
        else:
            self.map_generator = map_gen
        self.map_graphics_manager = MapGraphicsManager(self.map_generator.grid, 16, self.tileset)
        for item in self.map_graphics_manager.create_items():
            self.addItem(item)
        #self._init_grid()
        for p in self.map_generator.path:
            self.path_points.append(self.grid_to_scene(p))


        if self.multiplayer:
            # Create a vertical divider in the middle of the map
            divider_path = QPainterPath()
            divider_path.moveTo(width * cfg.TILE_SIZE/2, 0)
            divider_path.lineTo(width * cfg.TILE_SIZE/2, height * cfg.TILE_SIZE)
            
            self.map_divider = QGraphicsPathItem(divider_path)
            pen = QPen(QColor(255, 255, 0))  # Yellow divider
            pen.setWidth(3)
            pen.setStyle(Qt.DashLine)
            self.map_divider.setPen(pen)
            self.map_divider.setZValue(10)  # Above most game elements
            self.addItem(self.map_divider)
            self.map_width = width


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
        x = int(scene_pos.x() // 16)
        y = int(scene_pos.y() // 16)
        return (x, y)

    def game_over(self):
        """Handle game over state"""

        self.game_timer.stop()
        self.spawn_timer.stop()
        self.game_active = False
        self.game_over_signal.emit()
        # Show game over screen or reset game
        if self.game_state.record: self.history_recorder.record_event("game_over", {
            "final_score": self.game_state.score,
            "waves_completed": self.game_state.wave,
            "result": "defeat"
        })
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

        if self.game_state.record: self.history_recorder.record_event("wave_started", {
            "wave_number": self.game_state.wave,
            "enemies": [e.__class__.__name__ for e in self.game_state.enemies_to_spawn]
        })
        self.spawn_timer.start()
    def end_wave(self):
        """End the current wave of enemies"""
        self.game_state.wave_started = False
        self.game_state.wave += 1
        if self.game_state.record: self.history_recorder.record_event("wave_ended", {
            "wave_number": self.game_state.wave,
            "gold": self.game_state.gold,
            "lives": self.game_state.lives
        })
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
        path_int = []
        for p in self.path_points:
            path_int.append(self.scene_to_grid(p))
        self.history_recorder.start_recording({
            "game_mode": "single_player",
            "map": self.map_generator.grid,
            "path": path_int,
        })
        self.history_recorder.record_event("initial_state", {
            "gold": self.game_state.gold,
            "lives": self.game_state.lives,
            "wave": self.game_state.wave
        })
        
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
                if self.game_state.record: self.history_recorder.record_event("enemy_killed", {
                    "enemy_type": enemy.__class__.__name__,
                    "enemy_id": enemy.enemy_id,
                    "position": (enemy.pos().x(), enemy.pos().y())
                })
                self.removeItem(enemy)
                self.game_items['enemies'].remove(enemy)

                continue
            if enemy.pos() == self.path_points[-1]:
                self.game_state.lives -= 1

                if self.game_state.record: self.history_recorder.record_event("enemy_reached_end", {
                    "enemy_type": enemy.__class__.__name__,
                    "enemy_id": enemy.enemy_id,
                    "position": (enemy.pos().x(), enemy.pos().y())
                })
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
                if self.game_state.record: self.history_recorder.record_event("tower_shot", {
                    "tower_type": tower.__class__.__name__,
                    "tower_id": tower.tower_id,
                    "projectile_type": projectile.__class__.__name__,
                    "target_enemy": enemy.__class__.__name__,
                    "position": (tower.pos().x(), tower.pos().y())
                })
            tower.advance_animation(16)
    def _handle_projectile_hit(self, projectile, enemy):
        """Process projectile-enemy collision"""
        
        enemy._health -= projectile._damage
        projectile._pierce -= 1
        if enemy._health <= 0:
            projectile.parentTower.add_kill()
        if self.game_state.record: self.history_recorder.record_event("projectile_hit", {
            "projectile_type": projectile.__class__.__name__,
            "target_enemy": enemy.__class__.__name__,
            "position": (projectile.pos().x(), projectile.pos().y())
        })
    def _handle_projectile_death(self, projectile):
        """Process projectile expiration"""
        if isinstance(projectile, BombProjectile):
            explosion = ExplosionProjectile(projectile.pos(),None,projectile.parentTower,self.animations["explosion_projectile"])
            self.add_projectile(explosion)
        if self.game_state.record: self.history_recorder.record_event("projectile_expired", {
            "projectile_type": projectile.__class__.__name__,
            "position": (projectile.pos().x(), projectile.pos().y())
        })
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
        if self.game_state.record: self.history_recorder.record_event("tower_placed", {
            "tower_type": new_tower.__class__.__name__,
            "tower_id": new_tower.tower_id,
            "position": (pos.x(), pos.y()),
            "cost": new_tower.cost
        })
        
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
        if self.game_state.record: self.history_recorder.record_event("enemy_spawned", {
            "enemy_type": enemy.__class__.__name__,
            "enemy_id": enemy.enemy_id,
            "position": (enemy.pos().x(), enemy.pos().y())
        })


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
        if self.game_state.record: self.history_recorder.record_event("tower_sold", {
            "tower_type": tower.__class__.__name__,
            "tower_id": tower.tower_id,
            "position": (tower.pos().x(), tower.pos().y()),
            "refund": tower.cost // 2
        })
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
            if self.game_state.record: self.history_recorder.record_event("tower_upgraded", {
                "tower_type": tower.__class__.__name__,
                "tower_id": tower.tower_id,
                "position": (tower.pos().x(), tower.pos().y()),
                "upgrade_level": tower.upgrade_level,
                "cost": tower.upgrade_cost
            })
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
        if self.multiplayer:
            x_position = check_item.pos().x()
            map_center = self.map_width * cfg.TILE_SIZE / 2
            
            # Check if position is on the correct side for this player
            if self.player_side == "left" and x_position >= map_center:
                return False
            elif self.player_side == "right" and x_position < map_center:
                return False
        return True
    # ----------------------
    # Replay Methods
    # ----------------------
    def prepare_for_replay(self,path,grid):
        """Prepare the scene for replay"""
        # Clear current game state
        self.game_active = False
        self.reset_game_state(path,grid)

    def reset_game_state(self,path,grid):
        """Reset the game state for replaying"""
        # Clear all entities
        for item in self.items():
            self.removeItem(item)
        
        # Reset game state variables
        self.game_state.gold = cfg.BASE_GOLD
        self.game_state.lives = cfg.BASE_LIVES
        self.game_state.score = 0
        self.game_state.wave = 1
        self.game_state.record = False

        # Notify UI
        self.game_state.gold_changed.emit(self.game_state.gold)
        self.game_state.lives_changed.emit(self.game_state.lives)

        #load map
        self.path_points = []
        for p in path:
            self.path_points.append(self.grid_to_scene(p))
            print(p)
        self.map_graphics_manager = MapGraphicsManager(grid, 16, self.tileset)
        for item in self.map_graphics_manager.create_items():
            self.addItem(item)
        
        self.game_active = True
        self.game_timer.start()

    def cleanup_after_replay(self):
        """Clean up after replay finishes"""
        # Can be used to reset the game state if needed
        pass

    def replay_place_tower(self, tower_type, position):
        """Place a tower during replay"""

        # Create tower based on type
        tower = None
        print(f"Placing tower: {tower_type} at {position}")
        if tower_type == "BasicTower":
            tower = BasicTower(position, self.animations["basic_tower"])
        elif tower_type == "BombTower":
            tower = BombTower(position, self.animations["bomb_tower"])
        elif tower_type == "BoosterTower":
            tower = BoosterTower(position, self.animations["booster_tower"])

        if tower:
            self.addItem(tower)
            self.game_items['towers'].append(tower)
            print(f"Placed tower: {tower.__class__.__name__} at {position}")
            # No need to deduct gold in replay mode

    def replay_spawn_enemy(self, enemy_type,enemy_id):
        """Spawn an enemy during replay"""

        # Create enemy based on type
        enemy = None
        if enemy_type == "Rat":
            enemy = Rat(self.path_points,enemy_id,self.animations["rat"])
        elif enemy_type == "FastRat":
            enemy = FastRat(self.path_points,enemy_id, self.animations["fast_rat"])
        elif enemy_type == "GiantRat":
            enemy = GiantRat(self.path_points,enemy_id, self.animations["giant_rat"])

        if enemy:
            self.addItem(enemy)
            self.game_items['enemies'].append(enemy)
            
            enemy.setPos(self.path_points[0])
            print(f"Spawned enemy: {enemy.__class__.__name__} at {self.path_points[0]}")

    # def replay_kill_enemy(self, enemy_id, gold):
    #     """Kill an enemy during replay"""
    #     # In a real implementation, you would track enemies by ID
    #     # For simplicity, we'll just remove the first enemy
    #     if self.game_items['enemies']:
    #         enemy = next(filter(lambda e: e.enemy_id == enemy_id, self.game_items['enemies']))
    #         self.removeItem(enemy)
    #         self.game_items['enemies'].remove(enemy)

    #         # Update gold
    #         self.game_state.gold += gold
    #         self.game_state.gold_changed.emit(self.game_state.gold)
    #         print(f"Killed enemy: {enemy.__class__.__name__}, Gold: {gold}")

    def replay_start_wave(self, wave_number):
        """Start a wave during replay"""
        self.game_state.current_wave = wave_number
        self.game_state.wave_started = True
        print(f"Starting wave {wave_number}")

    def replay_end_wave(self):
        """End the current wave during replay"""
        self.game_state.wave_started = False
        print(f"Ending wave {self.game_state.current_wave}")

    def replay_game_end(self):
        """Handle game end during replay"""
        self.game_active = False
        print("Game ended during replay")
    def replay_tower_upgrade(self, tower_id, upgrade_level):
        """Upgrade a tower during replay"""
        # Find the tower by ID and upgrade it
        tower = next(filter(lambda t: t.tower_id == tower_id, self.game_items['towers']), None)
        if tower:
            tower.upgrade_level = upgrade_level
            tower.upgrade()
            print(f"Upgraded tower: {tower.__class__.__name__} to level {upgrade_level}")
        else:
            print(f"Tower with ID {tower_id} not found for upgrade")
    def replay_tower_sell(self, tower_id):
        """Sell a tower during replay"""
        # Find the tower by ID and remove it
        tower = next(filter(lambda t: t.tower_id == tower_id, self.game_items['towers']), None)
        if tower:
            self.removeItem(tower)
            self.game_items['towers'].remove(tower)
            print(f"Sold tower: {tower.__class__.__name__}")
        else:
            print(f"Tower with ID {tower_id} not found for selling")
    def update_timer_interval(self, interval):
        """Update the timer interval with playback speed for game speed"""
        self.game_timer.setInterval(interval)
        self.spawn_timer.setInterval(interval)
    # ----------------------
    # Network Methods
    # ----------------------
    def is_valid_position_for_player(self, pos, player_id):
        """Check if position is valid for the given player"""
        x_position = pos.x()
        map_center = self.map_width * cfg.TILE_SIZE / 2
        
        # Host gets left side, other player gets right
        if player_id == "host" and x_position >= map_center:
            return False
        elif player_id == "player2" and x_position < map_center:
            return False
            
        return True
    
    # Network event handlers
    def _on_network_connected(self, player_id):
        """Handle successful connection"""
        self.player_id = player_id
        
        # Set player side based on ID
        if player_id == "host":
            self.player_side = "left"
        else:
            self.player_side = "right"
        
        print(f"Connected as player: {player_id} on {self.player_side} side")
    
    def _on_network_disconnected(self):
        """Handle disconnection"""
        self.game_active = False
        print("Disconnected from network game")
    
    def _on_player_joined(self, player_id):
        """Handle another player joining"""
        print(f"Player joined: {player_id}")
        self.player_joined.emit(player_id)
    
    def _on_player_left(self, player_id):
        """Handle player leaving"""
        print(f"Player left: {player_id}")
        self.player_left.emit(player_id)
    
    def _on_network_error(self, error_msg):
        """Handle network error"""
        print(f"Network error: {error_msg}")
    
    def _on_network_event(self, event):
        """Process incoming network event"""
        event_type = event["type"]
        data = event["data"]
        sender_id = event["player_id"]
        
        # Don't process our own events that came back
        if sender_id == self.player_id:
            return
            
        # Handle different event types
        if event_type == GameNetworkEvent.PLACE_TOWER:
            # Another player placed a tower
            tower_type = data["tower_type"]
            pos = QPointF(data["x"], data["y"])
            
            # Create a temporary ghost tower with flag to avoid network loop
            ghost = GhostTowerItem({"name": tower_type})
            ghost._network_event = True
            self.add_tower(ghost, pos)
            
        elif event_type == GameNetworkEvent.START_WAVE:
            # Wave was started by host
            if not self.is_host:
                # Handle wave start as client
                super().start_wave()
                
        elif event_type == GameNetworkEvent.TOWER_UPGRADE:
            # Another player upgraded a tower
            tower_id = data["tower_id"]
            # Find and upgrade the tower
            # ...
            
        elif event_type == GameNetworkEvent.TOWER_SELL:
            # Another player sold a tower
            tower_id = data["tower_id"]
            # Find and remove the tower
            # ...
        
        # Emit the event for UI to handle
        self.network_event.emit(event)