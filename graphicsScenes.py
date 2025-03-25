from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QBrush, QColor, QPainterPath,QPen
from graphicItems import TowerItem, EnemyItem
class GameScene(QGraphicsScene):
    # Custom signals
    score_changed = Signal(int)
    lives_changed = Signal(int)
    tower_selected = Signal(object)
    items = []
    def __init__(self, grid_size=20, parent=None):
        super().__init__(parent)
        self.grid_size = grid_size
        self.game_active = False
        self.score = 0
        self.lives = 20
        
        # Game state containers
        self.towers = []
        self.enemies = []
        self.projectiles = []
        self.occupied_cells = set()
        
        # Setup game systems
        self._init_grid()
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
                item.setVisible(viewport_rect.intersects(item.sceneBoundingRect()))

    # ----------------------
    # Update Subsystems
    # ----------------------
    def _cleanup_items(self):
        pass
    def _update_enemies(self):
        """Process enemy movement and health"""
        for enemy in self.enemies:
            enemy.follow_path(self.path_points)
            if enemy.health <= 0:
                self._handle_enemy_death(enemy)

    def _update_towers(self):
        """Handle tower targeting and shooting"""
        for tower in self.towers:
            tower.acquire_target(self.enemies)
            if tower.should_fire():
                projectile = tower.create_projectile()
                self.add_projectile(projectile)

    def _update_projectiles(self):
        """Move projectiles and check lifespan"""
        for projectile in self.projectiles:
            projectile.update_position()
            if projectile.is_expired():
                self.removeItem(projectile)
                self.projectiles.remove(projectile)

    # ----------------------
    # Collision Detection
    # ----------------------
    def _check_collisions(self):
        """Detect and handle collisions"""
        for projectile in self.projectiles:
            colliding = self.items(projectile.pos())
            for item in colliding:
                if isinstance(item, EnemyItem):
                    self._handle_projectile_hit(projectile, item)

    # ----------------------
    # Item Management
    # ----------------------
    def add_tower(self, tower, grid_pos):
        """Register new tower"""
        if self._is_valid_placement(grid_pos):
            self.towers.append(tower)
            self.addItem(tower)
            self.occupied_cells.add(grid_pos)
            return True
        return False

    def add_projectile(self, projectile):
        """Register new projectile"""
        self.projectiles.append(projectile)
        self.addItem(projectile)

    def spawn_enemy(self):
        """Create and register new enemy"""
        enemy = EnemyItem()
        self.enemies.append(enemy)
        self.addItem(enemy)
        enemy.setPos(self.path_points[0])

    # ----------------------
    # User Interaction
    # ----------------------
    def mousePressEvent(self, event):
        """Handle tower placement"""
        if event.button() == Qt.LeftButton:
            scene_pos = event.scenePos()
            grid_pos = self._scene_to_grid(scene_pos)
            
            if self._is_valid_placement(grid_pos):
                tower = TowerItem()
                tower.setPos(scene_pos)
                self.add_tower(tower, grid_pos)

        super().mousePressEvent(event)

    # ----------------------
    # Helper Methods
    # ----------------------
    def _scene_to_grid(self, pos):
        """Convert scene coordinates to grid coordinates"""
        return (int(pos.x()) // self.grid_size,
                int(pos.y()) // self.grid_size)

    def _is_valid_placement(self, grid_pos):
        """Check if grid position is available"""
        return (
            grid_pos in self.grid and
            not self.grid[grid_pos]['occupied'] and
            self.grid[grid_pos]['walkable']
        )

    def _create_visual_path(self):
        """Generate visible path representation"""
        path = QPainterPath()
        path.moveTo(self.path_points[0])
        for point in self.path_points[1:]:
            path.lineTo(point)
        
        self.addPath(path, QPen(Qt.darkGreen, 30))
