import random
from enum import Enum
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem
from graphicItems import MapItem, PathItem,ObstacleItem
class TileType(Enum):
    EMPTY = 0
    PATH = 1
    START = 2
    END = 3
    BIG_OBSTACLE = 4
    SMALL_OBSTACLE = 5

    
    
class MapGenerator:
    def __init__(self,map_width, map_height):
        self.map_width = map_width
        self.map_height = map_height
        self.path = []
        self.grid = [[TileType.EMPTY.value for _ in range(map_width)] for _ in range(map_height)]
        self.generate_map_path()
        self.fill_path()
        self.fill_path_with_obstacles()
    def generate_map_path(self):

        start_y = random.randint(0, self.map_height - 1)
        end_y = random.randint(0, self.map_height - 1)
        start = (0, start_y)
        end = (self.map_height - 1, end_y)
        self.path = [start]
        current = start
        direction = 'right'

        while current[0] < end[0]:
            if direction == 'right':
                max_steps = end[0] - current[0]
                steps = random.randint(1, max_steps)
                new_x = current[0] + steps
                new_point = (new_x, current[1])
                self.path.append(new_point)
                current = new_point
                direction = 'vertical'
            else:
                possible_directions = []
                if current[1] < self.map_height - 1:
                    possible_directions.append(1)  # Up
                if current[1] > 0:
                    possible_directions.append(-1)  # Down
                if not possible_directions:
                    break
                dir_move = random.choice(possible_directions)
                if dir_move == 1:
                    max_steps = self.map_height - 1 - current[1]
                else:
                    max_steps = current[1]
                steps = random.randint(1, max_steps) if max_steps > 0 else 0
                new_y = current[1] + dir_move * steps
                new_point = (current[0], new_y)
                self.path.append(new_point)
                current = new_point
                direction = 'right'

        if current[1] != end[1]:
            self.path.append((current[0], end[1]))
        if self.path[-1] != end:
            self.path.append(end)
        print("Path generated:", self.path)

    def fill_path(self):

        # Fill the path
        for i in range(len(self.path) - 1):
            start = self.path[i]
            end_segment = self.path[i + 1]

            # Vertical movement
            if start[0] == end_segment[0]:
                y_min = min(start[1], end_segment[1])
                y_max = max(start[1], end_segment[1])
                for y in range(y_min, y_max + 1):
                    self.grid[y][start[0]] = TileType.PATH.value
            # Horizontal movement
            else:
                x_min = min(start[0], end_segment[0])
                x_max = max(start[0], end_segment[0])
                for x in range(x_min, x_max + 1):
                    self.grid[start[1]][x] = TileType.PATH.value

        # Mark start and end points
        self.grid[self.path[0][1]][self.path[0][0]] = TileType.START.value
        self.grid[self.path[-1][1]][self.path[-1][0]] = TileType.END.value

        
    def fill_path_with_obstacles(self, small_obstacles=15, big_obstacles=3):
        """
        Fill the map with obstacles.

        Parameters:
        small_obstacles (int): Number of small (1x1) obstacles to place
        big_obstacles (int): Number of big (3x4) obstacles to place
        """
        # Add small obstacles (1x1)
        small_placed = 0
        max_attempts = small_obstacles * 100  # Prevent infinite loop
        attempts = 0

        while small_placed < small_obstacles and attempts < max_attempts:
            x = random.randint(0, self.map_width - 1)
            y = random.randint(0, self.map_height - 1)
            attempts += 1

            # Check if position is empty
            if self.grid[y][x] == TileType.EMPTY.value:
                self.grid[y][x] = TileType.SMALL_OBSTACLE.value
                small_placed += 1

        # Add big obstacles (4x3)
        big_placed = 0
        max_attempts = big_obstacles * 100  # Prevent infinite loop
        attempts = 0

        while big_placed < big_obstacles and attempts < max_attempts:
            # For a 3x4 obstacle, the top-left corner must leave room for the rest
            x = random.randint(0, self.map_width - 3)  # 3 is the width
            y = random.randint(0, self.map_height - 4)  # 4 is the height
            attempts += 1

            # Check if all positions for this obstacle are empty
            can_place = True
            for i in range(4):  # height
                for j in range(3):  # width
                    if y + i < self.map_height and x + j < self.map_width:
                        if self.grid[y + i][x + j] != TileType.EMPTY.value:
                            can_place = False
                            break
                if not can_place:
                    break
                   
            if can_place:
                # Place the big obstacle
                for i in range(4):  # height
                    for j in range(3):  # width
                        self.grid[y + i][x + j] = TileType.BIG_OBSTACLE.value
                big_placed += 1
        
        for row in self.grid:
            print(" ".join(str(TileType(x).value) for x in row))

class MapGraphicsManager:
    def __init__(self, grid, tile_size, tileset):
        """
        Initialize the MapGraphicsManager with grid data, tile size, and tileset.
        
        :param grid: 2D list representing the map with cell types ('ground', 'path', 'small_obstacle', 'big_obstacle').
        :param tile_size: Size of each tile in pixels (assumed square).
        :param tileset: Dictionary mapping cell types to image paths.
        """
        self.grid = grid
        self.tile_size = tile_size
        self.tileset = tileset
        self.items = []
        self.processed = None  # Track processed cells to avoid overlaps
        
        # Load all pixmaps
        self.pixmaps = {}
        for key, path in self.tileset.items():
            self.pixmaps[key] = QPixmap(path)

    def create_items(self):
        """Create all graphics items with proper layering."""
        self.items = []
        rows = len(self.grid)
        cols = len(self.grid[0]) if rows > 0 else 0
        self.obstacle_processed = [[False]*cols for _ in range(rows)]

        # 1. Draw base layer (ground/path) for all cells
        for row in range(rows):
            for col in range(cols):
                base_type = 'path_c' if self.grid[row][col] == TileType.PATH.value else 'ground1'
                self._add_base_tile(row, col, base_type)

        # 2. Draw obstacles on top
        obstacle_order = [TileType.SMALL_OBSTACLE.value, TileType.BIG_OBSTACLE.value]
        for layer in obstacle_order:
            for row in range(rows):
                for col in range(cols):
                    if self.grid[row][col] == layer and not self.obstacle_processed[row][col]:
                        if layer == TileType.BIG_OBSTACLE.value:
                            self._add_big_obstacle(row, col)
                        else:
                            self._add_obstacle(row, col)
        return self.items

    def _add_base_tile(self, row, col, tile_type):
        """Add ground/path tiles unconditionally."""
        pixmap = self.pixmaps.get(tile_type)
        item = None
        if not pixmap:
            return
        if tile_type == 'path_c':
            item = PathItem(pixmap)
        else:
            item = MapItem(pixmap)
        item.setPos(col * self.tile_size, row * self.tile_size)
        self.items.append(item)
    def _add_obstacle(self, row, col):
        """Add single-cell obstacles."""
        key = 'small_obstacle'
        pixmap = self.pixmaps.get(key)
        if not pixmap:
            return
        item = ObstacleItem(pixmap)
        item.setPos(col * self.tile_size, row * self.tile_size)
        self.items.append(item)
        self.obstacle_processed[row][col] = True
    def _add_big_obstacle(self, row, col):
        """Add 3x4 obstacle and mark its area."""
        if (row + 3 > len(self.grid)) or (col + 4 > len(self.grid[0])):
            return
        pixmap = self.pixmaps.get('big_obstacle')
        if not pixmap:
            return
        # Add obstacle graphic
        item = ObstacleItem(pixmap)
        item.setPos(col * self.tile_size, row * self.tile_size)
        self.items.append(item)
        # Mark covered area
        for r in range(row, row+3):
            for c in range(col, col+4):
                if r < len(self.grid) and c < len(self.grid[0]):
                    self.obstacle_processed[r][c] = True