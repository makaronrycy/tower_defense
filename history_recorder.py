import time
import json
import xml.etree.ElementTree as ET
import xml.dom.minidom
from datetime import datetime
import os

class GameHistoryRecorder:
    """Records game events for later replay and analysis"""
    
    def __init__(self):
        self.start_time = time.time()
        self.events = []
        self.recording = False
        self.metadata = {
            "date": datetime.now().isoformat(),
            "game_mode": "single_player",
            "map_name": "default",
            "ip_address": ""
        }
        
    def start_recording(self, metadata=None):
        """Start recording game events"""
        self.start_time = time.time()
        self.events = []
        if metadata:
            self.metadata.update(metadata)
        self.recording = True
        
        # Record initial game state
        self.record_event("game_start", {
            "metadata": self.metadata
        })
        
    def stop_recording(self):
        """Stop recording game events"""
        if self.recording:
            self.record_event("game_end", {
                "duration": time.time() - self.start_time
            })
            self.recording = False
    def record_event(self, event_type, data):
        """Record a game event with current timestamp"""
        if not self.recording:
            return
            
        timestamp = time.time() - self.start_time
        
        event = {
            "time": round(timestamp, 3),
            "type": event_type,
            "data": data
        }
        print(f"Recorded event: {event}")
        
        self.events.append(event)
    def export_history(self):
        if not self.events:
            print("No events to export.")
            return
        history = {
            **self.metadata,
            "events": self.events
        }
        return history