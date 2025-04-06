from PySide6.QtCore import QObject, Signal, QTimer, QPointF
import time

class GameHistoryPlayer(QObject):
    """Plays back recorded game history"""
    
    # Signals
    event_played = Signal(dict)  # Emitted when an event is played
    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    playback_finished = Signal()
    playback_progress = Signal(float)  # Value between 0.0 and 1.0
    
    def __init__(self, scene=None):
        super().__init__()
        self.scene = scene  # Reference to game scene for visualization
        self.history = None
        self.events = []
        self.current_event_index = 0
        self.playback_speed = 1.0
        self.start_time = 0
        self.paused_at = 0
        self.is_paused = False
        self.is_playing = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._process_events)
        self.timer.setInterval(16)  # ~60fps updates
        
    def set_history(self, history):
        """Set history data for playback"""
        self.history = history
        self.events = history.get("events", [])
        self.current_event_index = 0
        self.is_paused = False
        self.is_playing = False
        return len(self.events) > 0
        
    def start(self, from_beginning=True):
        """Start playback of history"""
        if not self.events:
            print("No history loaded")
            return False
            
        if from_beginning:
            self.current_event_index = 0
            
        if self.scene:
            print(self.history.get("path"))
            path = None
            if isinstance(self.history.get("path"),tuple):
                path = self.history.get("path")[0]
            else:
                path = self.history.get("path")
                
            self.scene.prepare_for_replay(path, self.history.get("map"))
            
            
        self.is_paused = False
        self.is_playing = True
        self.start_time = time.time()
        
        if self.paused_at > 0 and not from_beginning:
            # Resume from pause by adjusting start time
            self.start_time = time.time() - self.paused_at
            
        self.paused_at = 0
        self.timer.start()
        self.playback_started.emit()
        return True
        
    def pause(self):
        """Pause playback"""
        if self.is_playing:
            self.timer.stop()
            self.is_paused = True
            self.paused_at = time.time() - self.start_time
            self.playback_paused.emit()
            
    def resume(self):
        """Resume paused playback"""
        if self.is_paused:
            self.start(from_beginning=False)
            
    def stop(self):
        """Stop playback"""
        self.timer.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_event_index = 0
        self.paused_at = 0
        
        if self.scene:
            self.scene.cleanup_after_replay()
            
        self.playback_stopped.emit()
        
    def set_speed(self, speed):
        """Set playback speed multiplier"""
        if speed <= 0:
            return
            
        if self.is_playing and not self.is_paused:
            # Adjust start_time to maintain correct position
            current_time = time.time()
            elapsed_real_time = current_time - self.start_time
            elapsed_game_time = elapsed_real_time * self.playback_speed
            
            # Calculate new start time with new speed
            self.start_time = current_time - (elapsed_game_time / speed)
            
        self.playback_speed = speed
        self.scene.update_timer_interval(speed)
    def _process_events(self):
        """Process events according to current time"""
        if not self.is_playing or self.current_event_index >= len(self.events):
            return
            
        current_time = time.time()
        elapsed_real_time = current_time - self.start_time
        game_time = elapsed_real_time * self.playback_speed
        
        # Calculate progress
        if len(self.events) > 0 and self.events[-1]["time"] > 0:
            progress = min(1.0, game_time / self.events[-1]["time"])
            self.playback_progress.emit(progress)
            
        # Process all events that should have occurred by now
        while (self.current_event_index < len(self.events) and 
               self.events[self.current_event_index]["time"] <= game_time):
            
            # Get current event and emit it
            event = self.events[self.current_event_index]
            self.event_played.emit(event)
            
            # Visualize in scene if available
            if self.scene:
                self._visualize_event(event)
                
            # Move to next event
            self.current_event_index += 1
            
            # Check if we reached the end
            if self.current_event_index >= len(self.events):
                self.timer.stop()
                self.is_playing = False
                self.playback_finished.emit()
                break
      
    def _visualize_event(self, event):
        """Visualize an event in the game scene"""
        if not self.scene:
            return
            
        event_type = event["type"]
        data = event["data"]
        if isinstance(data, str):
            data = eval(data)
        
        # Handle different event types
        if event_type == "game_start":
            path = None
            if isinstance(self.history.get("path"),tuple):
                path = self.history.get("path")[0]
            else:
                path = self.history.get("path")
            print(path)
            self.scene.reset_game_state(path, self.history.get("map"))
            
        elif event_type == "tower_placed":
            # Extract tower data
            print(f"data_type:{type(data)}")
            tower_type = data.get("tower_type")
            
            pos = data.get("position")
            self.scene.replay_place_tower(tower_type, QPointF(pos[0], pos[1]))
            
        elif event_type == "enemy_spawned":
            enemy_type = data.get("enemy_type")
            enemy_id = data.get("enemy_id")
            self.scene.replay_spawn_enemy(enemy_type,enemy_id)
            
        # elif event_type == "enemy_killed":
        #     enemy_id = data.get("enemy_id", 0)
        #     gold = int(data.get("gold", 0))
        #     self.scene.replay_kill_enemy(enemy_id, gold)
        elif event_type == "tower_upgraded":
            tower_id = data.get("tower_id", 0)
            upgrade_level = data.get("upgrade_type")
            self.scene.replay_tower_upgrade(tower_id, upgrade_level)
        elif event_type == "tower_sold":
            tower_id = data.get("tower_id", 0)
            self.scene.replay_tower_sell(tower_id)
            
        elif event_type == "wave_started":
            wave_number = int(data.get("wave_number", 1))
            self.scene.replay_start_wave(wave_number)
            
        elif event_type == "wave_ended":
            self.scene.replay_end_wave()
            
        elif event_type == "game_end":
            self.scene.replay_game_end()