import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import time
import os
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from PySide6.QtCore import QObject, Signal, Slot, QTimer, QPointF, QThread
from PySide6.QtWidgets import QMessageBox,QApplication
from enemies import Rat, GiantRat,FastRat
import config as cfg
from functools import wraps

def safe_for_training(method):
    """Decorator to make methods safe for training thread"""
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        # Check if we're in the main thread or training thread
        if not QThread.currentThread() is QApplication.instance().thread():
            # We're in training thread - use safe alternatives
            method_name = f"_{method.__name__}_training"
            if hasattr(self, method_name):
                return getattr(self, method_name)(*args, **kwargs)
            # Otherwise provide a dummy implementation
            return None
        # We're in main thread - use normal method
        return method(self, *args, **kwargs)
    return wrapper

class TowerDefenseEnv(gym.Env):
    """Custom Environment that follows gym interface for Tower Defense game"""
    metadata = {'render.modes': ['human']}

    def __init__(self, game_scene):
        super().__init__()
        self.game_scene = game_scene
        self.grid_size = (cfg.MAP_HEIGHT, cfg.MAP_WIDTH)
        
        # Define action and observation space
        # Action space: (tower_type, x, y)
        # Tower types: 0=none, 1=basic, 2=bomb, 3=booster
        self.action_space = spaces.MultiDiscrete([4, self.grid_size[0], self.grid_size[1]])
        
        # Observation space: grid state + resources + wave info
        # Grid: 0=empty, 1=tower, 2=path, 3=obstacle
        grid_shape = (self.grid_size[0], self.grid_size[1])
        
        # Add channels for different tower types, path, and enemies
        self.observation_space = spaces.Dict({
            'grid': spaces.Box(low=0, high=3, shape=(grid_shape[0], grid_shape[1], 4), dtype=np.int8),
            'resources': spaces.Box(low=0, high=np.inf, shape=(2,), dtype=np.float32),  # gold, lives
            'wave': spaces.Box(low=0, high=np.inf, shape=(1,), dtype=np.int32),  # current wave
        })
        
        self.reset()
    
    def _get_obs(self):
        """Convert game state to observation"""
        # Initialize grid observation with zeros
        grid_obs = np.zeros((self.grid_size[0], self.grid_size[1], 4), dtype=np.int8)
        
        # Add path information
        path_points = self.game_scene.path_points
        for point in path_points:
            # Convert scene coordinates to grid coordinates
            grid_x, grid_y = self._scene_to_grid(point)
            if 0 <= grid_x < self.grid_size[1] and 0 <= grid_y < self.grid_size[0]:
                grid_obs[grid_y, grid_x, 0] = 2  # Path
        
        # Add tower information
        for tower in self.game_scene.game_items['towers']:
            grid_x, grid_y = self._scene_to_grid(tower.pos())
            if 0 <= grid_x < self.grid_size[1] and 0 <= grid_y < self.grid_size[0]:
                # Determine tower type
                if tower.__class__.__name__ == "BasicTower":
                    grid_obs[grid_y, grid_x, 1] = 1
                elif tower.__class__.__name__ == "BombTower":
                    grid_obs[grid_y, grid_x, 1] = 2
                elif tower.__class__.__name__ == "BoosterTower":
                    grid_obs[grid_y, grid_x, 1] = 3
        
        # Add enemy information
        for enemy in self.game_scene.game_items['enemies']:
            grid_x, grid_y = self._scene_to_grid(enemy.pos())
            if 0 <= grid_x < self.grid_size[1] and 0 <= grid_y < self.grid_size[0]:
                grid_obs[grid_y, grid_x, 2] = 1
                # We could add more information about enemy types here
        
        # Resources and wave information
        resources = np.array([
            self.game_scene.game_state.gold,
            self.game_scene.game_state.lives,
        ], dtype=np.float32)
        
        wave = np.array([self.game_scene.game_state.wave], dtype=np.int32)
        
        return {
            'grid': grid_obs,
            'resources': resources,
            'wave': wave
        }
    
    def _scene_to_grid(self, pos):
        """Convert scene coordinates to grid coordinates"""
        return self.game_scene.scene_to_grid(pos)
    
    def _grid_to_scene(self, grid_pos):
        """Convert grid coordinates to scene coordinates"""
        return self.game_scene.grid_to_scene(grid_pos)
    
    def step(self, action):
        """Execute one time step within the environment"""
        tower_type, grid_x, grid_y = action
        
        # Convert grid coordinates to scene coordinates
        scene_pos = self._grid_to_scene((grid_x, grid_y))
        
        # Initialize reward
        reward = 0.0
        done = False
        info = {}
        
        # Track state before action for comparison
        prev_gold = self.game_scene.game_state.gold
        prev_lives = self.game_scene.game_state.lives
        prev_score = self.game_scene.game_state.score
        prev_enemies_count = len(self.game_scene.game_items['enemies'])
        
        # Start a new wave if none is active
        if (not self.game_scene.game_state.wave_started and 
            len(self.game_scene.game_state.enemies_to_spawn) == 0 and 
            len(self.game_scene.game_items['enemies']) == 0):
            # Instead of modifying multiplayer settings, use the training-specific method
            if hasattr(self.game_scene, 'start_wave_training'):
                self.game_scene.start_wave_training()
            else:
                # Fallback to the original method with modifications
                original_multiplayer = self.game_scene.multiplayer
                original_is_host = self.game_scene.is_host
                self.game_scene.multiplayer = False
                self.game_scene.is_host = True
                self.game_scene.start_wave()
                self.game_scene.multiplayer = original_multiplayer
                self.game_scene.is_host = original_is_host
            
            # Give small reward for starting a new wave
            reward += 2.0
        
        # Process the action - place a tower if type > 0
        if tower_type > 0:
            # Ensure tower_type is an integer
            tower_type = int(tower_type)
            tower_names = {1: "basic", 2: "bomb", 3: "booster"}
            tower_type_name = tower_names.get(tower_type)
            
            if tower_type_name:
                # Only attempt to place tower if enough gold
                tower_costs = {"basic": 20, "bomb": 200, "booster": 80}
                if self.game_scene.game_state.gold >= tower_costs[tower_type_name]:
                    # Check if placement is valid
                    from graphicItems import GhostTowerItem
                    # Use tower_config instead
                    tower_config = {
                        "type": tower_type_name,
                        "cost": tower_costs[tower_type_name],
                    }
                    # Create a ghost tower to check placement validity
                    temp_tower = GhostTowerItem(tower_config)
                    temp_tower.setPos(scene_pos)
                    
                    if self.game_scene.is_valid_position(temp_tower):
                        self.game_scene.add_tower(temp_tower, scene_pos)
                        self.game_scene.game_state.gold -= tower_costs[tower_type_name]
                        # Small reward for tower placement
                        reward += 0.5
                    else:
                        # Penalty for invalid placement attempt
                        reward -= 0.2
                else:
                    # Penalty for trying to place unaffordable tower
                    reward -= 0.1
        
        # Run game for a short period to see effects - UPDATED
        for _ in range(5):  # Simulate 5 game ticks
            self.game_scene.advance_for_training()  # Use non-timer version instead
            
            # Check for enemies to spawn with a thread-safe method that doesn't check timers
            if (self.game_scene.game_state.wave_started and 
                self.game_scene.game_state.enemies_to_spawn):
                # Don't check spawn_timer.isActive() which causes the thread error
                self._handle_enemy_spawn()
    
        # Calculate rewards based on game state changes
        # Reward for killing enemies
        enemies_killed = prev_enemies_count - len(self.game_scene.game_items['enemies'])
        reward += enemies_killed * 1.0
        
        # Reward for score increase
        score_increase = self.game_scene.game_state.score - prev_score
        reward += score_increase * 0.01
        
        # Penalty for losing lives
        lives_lost = prev_lives - self.game_scene.game_state.lives
        reward -= lives_lost * 5.0
        
        # Check if game is over (either won or lost)
        if self.game_scene.game_state.lives <= 0:
            done = True
            reward -= 50.0  # Big penalty for losing
            
        if not self.game_scene.game_state.wave_started and not self.game_scene.game_state.enemies_to_spawn:
            # Wave ended successfully
            reward += 10.0  # Reward for completing wave
            
            # Check if there are more waves
            if self.game_scene.game_state.wave > 10:  # Assuming game is won after 10 waves
                done = True
                reward += 100.0  # Big reward for winning
        
        # Return the new observation, reward, done flag, and info dict
        return self._get_obs(), reward, done, False, info

    def _handle_enemy_spawn(self):
        """Handle spawning an enemy during training"""
        if not self.game_scene.game_state.enemies_to_spawn:
            return
            
        # Spawn one enemy manually
        enemy_type = self.game_scene.game_state.enemies_to_spawn[0]
        self.game_scene.game_state.enemies_to_spawn.pop(0)
        
        # For training, create a more complete mock enemy with required methods
        enemy = type('MockEnemy', (), {
            'pos': lambda: self.game_scene.path_points[0],
            'health': 10, 
            '_health': 10,
            'enemy_id': 'training_enemy',
            'value': 5,
            # Add missing methods
            'advance_animation': lambda _: None,  # No-op animation function
            '__class__': type('MockClass', (), {'__name__': enemy_type.capitalize()}),
            # Make it properly handle movement along path
            'path_points': self.game_scene.path_points,
            'current_point': 0,
            'setPos': lambda pos: None  # No-op position setter
        })
        
        self.game_scene.game_items['enemies'].append(enemy)

    def reset(self, seed=None, options=None):
        """Reset the environment to its initial state"""
        super().reset(seed=seed)
        
        # Thread-safe game state reset 
        if hasattr(self.game_scene, 'reset_game'):
            # Use signals if called from worker thread
            if QThread.currentThread() is not QApplication.instance().thread():
                # Handle reset without timers for training
                self._reset_for_training()
            else:
                self.game_scene.reset_game_state()
        
        # Start the game if it's not active - safely
        if not self.game_scene.game_active:
            if QThread.currentThread() is not QApplication.instance().thread():
                # Just set the flag for training purposes
                self.game_scene.game_active = True
            else:
                self.game_scene.start_game()
        
        return self._get_obs(), {}

    def _reset_for_training(self):
        """Reset game state without timers for training"""
        # Reset core game values without timers
        self.game_scene.game_state.gold = cfg.BASE_GOLD
        self.game_scene.game_state.lives = cfg.BASE_LIVES
        self.game_scene.game_state.score = 0
        self.game_scene.game_state.wave = 1
        self.game_scene.game_active = True
        
        # Clear existing game entities
        for item_category in self.game_scene.game_items:
            for item in list(self.game_scene.game_items[item_category]):
                self.game_scene.removeItem(item)
            self.game_scene.game_items[item_category] = []
        
        # Reset wave state
        self.game_scene.game_state.wave_started = False
        self.game_scene.game_state.enemies_to_spawn = []
        
        # Prepare to start first wave
        # Save original multiplayer state
        original_multiplayer = self.game_scene.multiplayer
        original_is_host = self.game_scene.is_host
        
        # Temporarily adjust settings to ensure wave starts
        self.game_scene.multiplayer = False
        self.game_scene.is_host = True
        
        # Prepare the first wave without timers
        self.game_scene.start_wave()
        
        # Restore original settings
        self.game_scene.multiplayer = original_multiplayer
        self.game_scene.is_host = original_is_host

    def render(self):
        """Render the environment to the screen"""
        # Game is already being rendered by Qt
        pass

    def close(self):
        """Clean up resources"""
        pass


class TowerDefenseAI(QObject):
    """AI controller for Tower Defense game"""
    action_performed = Signal(object)  # Signal when AI takes action
    thinking = Signal()  # Signal when AI is thinking
    request_start_timer = Signal()  # Add new signal
    request_stop_timer = Signal()   # Add new signal
    
    def __init__(self, game_scene, parent=None):
        # Add this to your existing __init__ method
        super().__init__(parent)
        self.game_scene = game_scene
        self.env = TowerDefenseEnv(game_scene)
        
        self.model_path = "models/tower_defense_ai"
        self.model = None
        self.active = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.step)
        self.think_time = 500  # milliseconds between decisions
        self.request_start_timer.connect(self._start_timer_in_main_thread)
        self.request_stop_timer.connect(self._stop_timer_in_main_thread)
        
        # Track previously attempted positions
        self.attempted_positions = set()
        self.failed_attempts_threshold = 3  # Allow a few failures before forcing diversity

    @Slot()
    def _start_timer_in_main_thread(self):
        """Safely start timer in main thread"""
        self.timer.start(self.think_time)
        
    @Slot()
    def _stop_timer_in_main_thread(self):
        """Safely stop timer in main thread"""
        self.timer.stop()
        
    def load_model(self):
        """Load the trained model if available"""
        try:
            # Make sure directory exists
            os.makedirs("models", exist_ok=True)
            
            # Ensure model_path doesn't already have .zip extension
            if self.model_path.endswith('.zip'):
                model_path = self.model_path[:-4]  # Remove .zip extension
            else:
                model_path = self.model_path
                
            self.model_path = model_path  # Store clean path
                
            # Check if model file exists WITH .zip extension
            if os.path.exists(f"{model_path}.zip"):
                print(f"Loading model from {model_path}.zip")
                self.model = PPO.load(model_path, env=self.env)
                return True
            else:
                # Create a new model with default parameters
                print(f"No model found at {model_path}.zip - creating new model")
                self.model = PPO("MultiInputPolicy", self.env, verbose=1)
                return False
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self):
        """Start AI controlling the game"""
        if not self.model:
            self.load_model()
        
        print("Starting AI controller...")
        
        # Try to place a tower - loop through more positions
        if self.game_scene.game_state.gold >= 20:
            placed = False
            for x in range(3, 15):
                for y in range(3, 15):
                    if placed:
                        break
                    
                    try:
                        pos = self.env._grid_to_scene((x, y))
                        from towers import BasicTower
                        tower = BasicTower(pos, self.game_scene.animations["basic_tower"])
                        
                        if self.game_scene.is_valid_position(tower):
                            print(f"AI placing initial tower at {x},{y}")
                            self.game_scene.game_items['towers'].append(tower)
                            self.game_scene.addItem(tower)
                            self.game_scene.game_state.gold -= 20
                            placed = True
                    except Exception as e:
                        print(f"Error placing initial tower: {e}")
                if placed:
                    break
        
        self.active = True
        self.request_start_timer.emit()
        
        # Check timer status
        QTimer.singleShot(1000, lambda: print(f"AI timer active: {self.timer.isActive()}"))
    
    def stop(self):
        """Stop AI control"""
        self.active = False
        self.request_stop_timer.emit()  # Use signal instead
    
    def step(self):
        """Perform one AI action step"""
        if not self.active or not self.game_scene.game_active:
            return
        
        self.thinking.emit()
        
        # Check if we need to start a wave
        if (not self.game_scene.game_state.wave_started and 
            len(self.game_scene.game_state.enemies_to_spawn) == 0 and 
            len(self.game_scene.game_items['enemies']) == 0):
            print("AI is starting a new wave...")
            # Use the real game's wave starting mechanism
            self.game_scene.start_wave()
            # Reset the position tracking at the start of each wave
            self.attempted_positions = set()
    
        # Get current observation
        obs = self.env._get_obs()
        
        # DEBUG: Print current gold
        print(f"AI step - Current gold: {self.game_scene.game_state.gold}")
        
        # If model exists, use it with occasional exploration; otherwise use direct placement
        if self.model:
            # Use non-deterministic prediction occasionally to encourage exploration
            use_deterministic = random.random() > 0.2  # 80% deterministic, 20% exploration
            
            # Predict action
            action, _ = self.model.predict(obs, deterministic=use_deterministic)
            
            # Ensure action components are of correct type
            action = [int(action[0]), int(action[1]), int(action[2])]
            
            # Check if this position has been tried too many times
            pos_key = f"{action[1]},{action[2]}"
            if pos_key in self.attempted_positions:
                print(f"Position {pos_key} already attempted - forcing diversity")
                # Force a different position by using random placement
                action = self._generate_diverse_placement()
            
            print(f"AI action: tower_type={action[0]}, x={action[1]}, y={action[2]}")
        else:
            # Direct placement algorithm for untrained model
            action = self._generate_diverse_placement()
        
        # Execute action directly on game scene
        success = self._execute_action_in_game(action)
        
        # If placement failed, add to attempted positions to avoid retrying
        if not success and action[0] > 0:  # Only track if tower placement was attempted
            pos_key = f"{action[1]},{action[2]}"
            self.attempted_positions.add(pos_key)
        
        # Emit signal
        self.action_performed.emit(action)
        
        # Check if game is over
        if self.game_scene.game_state.lives <= 0:
            self.stop()

    def _generate_diverse_placement(self):
        """Generate a placement action that tries to be diverse"""
        import random
        
        # Try to place a tower if we have gold
        if self.game_scene.game_state.gold >= 20:  # Cost of basic tower
            # Decide which tower type to place based on available gold
            if self.game_scene.game_state.gold >= 200:
                tower_type = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]  # Basic, bomb, booster
            elif self.game_scene.game_state.gold >= 80:
                tower_type = random.choices([1, 3], weights=[0.8, 0.2])[0]  # Basic or booster
            else:
                tower_type = 1  # Basic tower
            
            # Try up to 20 random positions
            for _ in range(20):
                grid_x = random.randint(1, self.env.grid_size[1]-2)
                grid_y = random.randint(1, self.env.grid_size[0]-2)
                
                # Check if we've already tried this position
                pos_key = f"{grid_x},{grid_y}"
                if pos_key in self.attempted_positions:
                    continue
                    
                # Check if position is valid
                scene_pos = self.env._grid_to_scene((grid_x, grid_y))
                from graphicItems import GhostTowerItem
                tower_costs = {"basic": 20, "bomb": 200, "booster": 80}
                tower_names = {1: "basic", 2: "bomb", 3: "booster"}
                ghost = GhostTowerItem({"type": tower_names[tower_type], "cost": tower_costs[tower_names[tower_type]]})
                ghost.setPos(scene_pos)
                
                if self.game_scene.is_valid_position(ghost):
                    return [tower_type, grid_x, grid_y]
        
        # Default to no action
        return [0, 0, 0]

    def _execute_action_in_game(self, action):
        """Execute AI action directly on the game scene"""
        tower_type, grid_x, grid_y = action
        
        # Convert grid coordinates to scene coordinates
        scene_pos = self.env._grid_to_scene((grid_x, grid_y))
        
        # Initialize success flag
        success = False
        
        # Process the action - place a tower if type > 0
        if tower_type > 0:
            tower_names = {1: "basic", 2: "bomb", 3: "booster"}
            tower_type_name = tower_names.get(tower_type)
            
            if tower_type_name:
                # Check if we have enough gold
                tower_costs = {"basic": 20, "bomb": 200, "booster": 80}
                cost = tower_costs.get(tower_type_name, 0)
                
                print(f"Attempting to place {tower_type_name} tower at ({grid_x},{grid_y})")
                print(f"Available gold: {self.game_scene.game_state.gold}, Cost: {cost}")
                
                if self.game_scene.game_state.gold >= cost:
                    try:
                        # Create a tower directly instead of using ghost tower
                        from towers import BasicTower, BombTower, BoosterTower
                        
                        if tower_type_name == "basic":
                            tower = BasicTower(scene_pos, self.game_scene.animations["basic_tower"])
                            valid = self.game_scene.is_valid_position(tower)
                            print(f"Position valid: {valid}")
                            if valid:
                                self.game_scene.game_items['towers'].append(tower)
                                self.game_scene.addItem(tower)
                                self.game_scene.game_state.gold -= cost
                                success = True
                                print(f"✓ Basic tower placed at ({grid_x},{grid_y})")
                                return success
                        
                        # If direct placement failed, try using the ghost tower method
                        from graphicItems import GhostTowerItem
                        ghost_tower = GhostTowerItem({"type": tower_type_name, "cost": cost})
                        ghost_tower.setPos(scene_pos)
                        ghost_tower.name = tower_type_name  # Ensure name property exists
                        
                        valid = self.game_scene.is_valid_position(ghost_tower)
                        print(f"Ghost position valid: {valid}")
                        
                        if valid:
                            # Try both methods of tower placement
                            try:
                                # Method 1: add_tower method
                                self.game_scene.add_tower(ghost_tower, scene_pos)
                                print(f"✓ Tower placed using add_tower at ({grid_x},{grid_y})")
                                success = True
                            except Exception as e1:
                                print(f"Error with add_tower: {e1}")
                                
                                # Method 2: Direct placement
                                try:
                                    if tower_type_name == "basic":
                                        tower = BasicTower(scene_pos, self.game_scene.animations["basic_tower"])
                                    elif tower_type_name == "bomb":
                                        tower = BombTower(scene_pos, self.game_scene.animations["bomb_tower"])
                                    elif tower_type_name == "booster":
                                        tower = BoosterTower(scene_pos, self.game_scene.animations["booster_tower"])
                                        
                                    self.game_scene.game_items['towers'].append(tower)
                                    self.game_scene.addItem(tower)
                                    self.game_scene.game_state.gold -= cost
                                    print(f"✓ Tower placed directly at ({grid_x},{grid_y})")
                                    success = True
                                except Exception as e2:
                                    print(f"Error with direct placement: {e2}")
                                    
                    except Exception as e:
                        print(f"Error during tower placement: {e}")
                        import traceback
                        traceback.print_exc()
        
        return success  # Return False if placement failed

    def train(self, timesteps=10000):
        """Train the model for a number of timesteps"""
        if not self.model:
            self.load_model()
        
        # Create directory for models if it doesn't exist
        os.makedirs("models", exist_ok=True)
        
        # Training callback for saving
        class SaveCallback(BaseCallback):
            def __init__(self, save_freq=1000, save_path="models", verbose=1):
                super().__init__(verbose)
                self.save_freq = save_freq
                self.save_path = save_path
            
            def _on_step(self):
                if self.n_calls % self.save_freq == 0:
                    self.model.save(f"{self.save_path}/tower_defense_ai")
                return True
        
        # Train the model
        try:
            self.model.learn(total_timesteps=timesteps, callback=SaveCallback())
            self.model.save(self.model_path)
            return True
        except Exception as e:
            print(f"Error during training: {e}")
            return False


class TrainingWorker(QThread):
    """Worker thread for training the AI model"""
    progress = Signal(int)
    completed = Signal(bool)
    
    def __init__(self, ai, timesteps=10000):
        super().__init__()
        self.ai = ai
        self.timesteps = timesteps
    
    def run(self):
        """Run the training process"""
        try:
            # Create a dedicated environment for training
            # that doesn't touch the UI directly
            
            # Clone essential game scene properties without sharing timer objects
            from copy import deepcopy
            
            # Create a training-specific environment that doesn't interact with UI timers
            class TrainingGameScene:
                def __init__(self, real_scene):
                    # Copy only the data we need, not timers or Qt objects
                    self.map_generator = real_scene.map_generator
                    self.game_items = {"towers": [], "enemies": [], "projectiles": []}
                    self.path_points = deepcopy(real_scene.path_points)
                    self.animations = real_scene.animations  # Just reference, won't modify
                    self.multiplayer = False
                    self.is_host = True
                    self.game_active = True
                    
                    # Create fresh game state without signals
                    self.game_state = type('GameState', (), {
                        'gold': cfg.BASE_GOLD,
                        'lives': cfg.BASE_LIVES,
                        'score': 0,
                        'wave': 1,
                        'wave_started': False,
                        'enemies_to_spawn': []
                    })
                    
                    # Mock the timer properties that training code checks
                    self.spawn_timer = type('MockTimer', (), {'isActive': lambda: False})
                    
                def advance_for_training(self):
                    # Add actual simulation code
                    # Simple simulation of game advancement
                    # Process enemies
                    for enemy in list(self.game_items['enemies']):
                        # Move enemies along path or remove them
                        if hasattr(enemy, 'current_point'):
                            enemy.current_point += 1
                            if enemy.current_point >= len(self.path_points):
                                # Enemy reached end
                                self.game_state.lives -= 1
                                self.game_items['enemies'].remove(enemy)
                            elif random.random() < 0.1:  # 10% chance to "kill" enemies
                                self.game_state.score += enemy.value
                                self.game_state.gold += enemy.value
                                self.game_items['enemies'].remove(enemy)
                
                def start_wave_training(self):
                    # Simplified wave start logic without timers
                    self.game_state.wave_started = True
                    # Add mock enemies
                    self.game_state.enemies_to_spawn = ["rat"] * 10
                    
                def scene_to_grid(self, pos):
                    # Grid conversion without Qt dependencies
                    x = int(pos.x() // 16)
                    y = int(pos.y() // 16)
                    return (x, y)
                    
                def grid_to_scene(self, grid_pos):
                    # Scene conversion without Qt dependencies
                    return QPointF(grid_pos[0] * 16, grid_pos[1] * 16)
                    
                def is_valid_position(self, tower):
                    # Simplified check for training
                    return True
                    
                def add_tower(self, tower, pos):
                    # Simplified tower adding for training
                    pass
                
                def removeItem(self, item):
                    """Safe version of removeItem that works with mock objects"""
                    # For real QGraphicsItems, we would need to remove from the scene
                    # For mock objects in training, just remove from our lists
                    for category in self.game_items:
                        if item in self.game_items[category]:
                            self.game_items[category].remove(item)
                            return
            
            # Create a training scene that won't affect timers
            training_scene = TrainingGameScene(self.ai.game_scene)
            
            # Create temporary environment with our safe scene
            from tower_defense_ai import TowerDefenseEnv
            env = TowerDefenseEnv(training_scene)
            self.ai.model_path = validate_model_path(self.ai.model_path)
            # Load or create model
            if os.path.exists(f"{self.ai.model_path}.zip"):
                model = PPO.load(self.ai.model_path, env=env)
            else:
                # Create model with higher exploration parameters
                model = PPO(
                    "MultiInputPolicy", 
                    env, 
                    verbose=1,
                    # Increase entropy coefficient to encourage exploration
                    ent_coef=0.01,  
                    # Use a larger learning rate
                    learning_rate=0.0003,
                    # Larger batch size
                    batch_size=64,
                    # More steps per update
                    n_steps=2048
                )
            
            # Rest of training code remains the same...
            # Create directory for models if it doesn't exist
            os.makedirs("models", exist_ok=True)
            
            # Custom callback to report progress
            class ProgressCallback(BaseCallback):
                def __init__(self, progress_signal, total_timesteps, model_path):
                    super().__init__(verbose=1)
                    self.progress_signal = progress_signal
                    self.total_timesteps = total_timesteps
                    self.model_path = model_path
                
                def _on_step(self):
                    progress = int((self.n_calls / self.total_timesteps) * 100)
                    self.progress_signal.emit(progress)
                    if self.n_calls % 1000 == 0:
                        try:
                            # Always save WITHOUT .zip extension - Stable Baselines adds it automatically
                            if self.model_path.endswith('.zip'):
                                path = self.model_path[:-4]
                            else:
                                path = self.model_path
                                
                            self.model.save(path)
                            print(f"Saved checkpoint to {path}.zip")
                        except Exception as e:
                            print(f"Warning: Could not save model: {e}")
                    return True
            
            # Train the model
            callback = ProgressCallback(self.progress, self.timesteps, self.ai.model_path)
            model.learn(total_timesteps=self.timesteps, callback=callback)
            
            # Ensure clean path without .zip extension
            save_path = self.ai.model_path
            if save_path.endswith('.zip'):
                save_path = save_path[:-4]

            # Save the model
            model.save(save_path)
            print(f"Training complete, model saved to {save_path}.zip")

            # Update the AI's model
            self.ai.model = model
            
            self.completed.emit(True)
        except Exception as e:
            print(f"Training error: {e}")
            import traceback
            traceback.print_exc()  # Print the full stack trace
            self.completed.emit(False)

def validate_model_path(path):
    """Validate and fix model path, returning a clean path without .zip extension"""
    # Strip .zip extension if present
    if path.endswith('.zip'):
        path = path[:-4]
        
    # Ensure directory exists
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
        
    # Return clean path
    return path