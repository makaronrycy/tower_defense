from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QRadioButton, QButtonGroup, QGroupBox, QSlider, QComboBox, 
    QFileDialog, QMessageBox, QFormLayout, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QRegularExpression, Slot
from PySide6.QtGui import QRegularExpressionValidator
import json
import xml.etree.ElementTree as ET
import xml.dom.minidom
import os
import pymongo
from datetime import datetime
from history.history_player import GameHistoryPlayer

class GameHistoryManager:
    """Manages saving and loading game history in different formats"""
    
    @staticmethod
    def save_json(history, filename):
        """Save game history to JSON file"""
        with open(filename, 'w') as f:
            json.dump(history, f, indent=2)
    
    @staticmethod
    def load_json(filename):
        """Load game history from JSON file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON: {e}")
            return None
    
    @staticmethod
    def save_xml(history, filename):
        """Save game history to XML file"""
        root = ET.Element("GameHistory")
        
        # Add metadata
        metadata = ET.SubElement(root, "Metadata")
        ET.SubElement(metadata, "Date").text = history.get("date", datetime.now().isoformat())
        ET.SubElement(metadata, "GameMode").text = history.get("game_mode", "")
        ET.SubElement(metadata, "ServerIP").text = history.get("server_ip", "")
        # Add map data if available
        if "map" in history:
            map_elem = ET.SubElement(metadata, "Map")
            map_data = history.get("map", [])
            for row in map_data:
                row_elem = ET.SubElement(map_elem, "Row")
                row_elem.text = " ".join(str(cell) for cell in row)

        # Add path data if available
        if "path" in history:
            path_elem = ET.SubElement(metadata, "Path")
            path_data = history.get("path", [])
            for point in path_data:
                point_elem = ET.SubElement(path_elem, "Point")
                x_elem = ET.SubElement(point_elem, "X")
                x_elem.text = str(point[0])
                y_elem = ET.SubElement(point_elem, "Y")
                y_elem.text = str(point[1])
        # Add events
        events = ET.SubElement(root, "Events")
        for event in history.get("events", []):
            event_elem = ET.SubElement(events, "Event")
            ET.SubElement(event_elem, "Time").text = str(event.get("time", 0))
            ET.SubElement(event_elem, "Type").text = event.get("type", "")
            ET.SubElement(event_elem, "Data").text = str(event.get("data", ""))
        
        # Pretty print XML and save
        xml_str = ET.tostring(root, encoding='utf-8')
        dom = xml.dom.minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        with open(filename, 'w') as f:
            f.write(pretty_xml)
    
    @staticmethod
    def load_xml(filename):
        """Load game history from XML file"""
        try:
            tree = ET.parse(filename)
            root = tree.getroot()
            
            history = {
                "date": root.find("./Metadata/Date").text,
                "game_mode": root.find("./Metadata/GameMode").text,
                "server_ip": root.find("./Metadata/ServerIP").text,
                # Extract map data if available
                "map": [],
                "events": []
            }
            if root.find("./Metadata/Map") is not None:
                map_data = []
                for row_elem in root.findall("./Metadata/Map/Row"):
                    if row_elem.text:
                        map_data.append([int(cell) for cell in row_elem.text.split()])
                history["map"] = map_data

            # Extract path data if available
            
            if root.find("./Metadata/Path") is not None:
                path_data = []
                for point_elem in root.findall("./Metadata/Path/Point"):
                    x = int(point_elem.find("X").text)
                    y = int(point_elem.find("Y").text)
                    
                    path_data.append([x, y])
                history["path"] = path_data,
            
                

            
            for event_elem in root.findall("./Events/Event"):
                event = {
                    "time": float(event_elem.find("Time").text),
                    "type": event_elem.find("Type").text,
                    "data": event_elem.find("Data").text
                }
                history["events"].append(event)
                
            return history
        except Exception as e:
            print(f"Error loading XML: {e}")
            return None
    
    @staticmethod
    def save_mongodb(history, db_uri="mongodb://localhost:27017/"):
        """Save game history to MongoDB"""
        try:
            client = pymongo.MongoClient(db_uri)
            db = client["tower_defense"]
            collection = db["game_history"]
            
            # Add timestamp if not present
            if "date" not in history:
                history["date"] = datetime.now().isoformat()
                
            result = collection.insert_one(history)
            return str(result.inserted_id)
        except Exception as e:
            print(f"MongoDB save error: {e}")
            return None
    
    @staticmethod
    def load_mongodb(db_uri="mongodb://localhost:27017/", query=None):
        """Load game histories from MongoDB"""
        try:
            client = pymongo.MongoClient(db_uri)
            db = client["tower_defense"]
            collection = db["game_history"]
            
            if query is None:
                query = {}
                
            return list(collection.find(query))
        except Exception as e:
            print(f"MongoDB load error: {e}")
            return []


class ConfigurationDialog(QDialog):
    """Game configuration dialog with history management"""
    
    config_saved = Signal(dict)  # Emitted when configuration is saved
    
    def __init__(self, parent=None, scene=None):
        super().__init__(parent)
        self.setWindowTitle("Game Configuration")
        self.setMinimumWidth(500)
        self.scene = scene  # Store game scene reference
        self.history_manager = GameHistoryManager()
        self.current_history = scene.history_recorder.export_history() if scene else None
        self.playback_speed = 1.0
        self.history_player = None
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Game Mode Selection
        self.create_game_mode_group(main_layout)
        
        # Network Settings
        self.create_network_settings_group(main_layout)
        
        # History Management
        self.create_history_management_group(main_layout)
        
        # Playback Controls
        self.create_playback_controls_group(main_layout)
        
        # Bottom Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Configuration and start new game")
        self.save_button.clicked.connect(self.save_configuration)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def create_network_settings_group(self, parent_layout):
        self.network_group = QGroupBox("Network Settings")
        layout = QFormLayout()
        
        # IP Address input with validation
        self.ip_input = QLineEdit()
        self.ip_input.setInputMask("000.000.000.000;_")
        self.ip_input.setText("127.000.000.001")
        self.ip_input.setToolTip("Enter the server IP address")
        
        # Port input with validation
        self.port_input = QLineEdit()
        port_validator = QRegularExpressionValidator(QRegularExpression("^[0-9]{1,5}$"))
        self.port_input.setValidator(port_validator)
        self.port_input.setText("8080")
        self.port_input.setToolTip("Enter the server port (1-65535)")
        
        layout.addRow("Server IP:", self.ip_input)
        layout.addRow("Port:", self.port_input)
        
        self.network_group.setLayout(layout)
        self.network_group.setEnabled(False)  # Disabled by default
        parent_layout.addWidget(self.network_group)
    
    def create_history_management_group(self, parent_layout):
        group_box = QGroupBox("Game History")
        layout = QVBoxLayout()
        
        # Save buttons
        save_layout = QHBoxLayout()
        self.save_json_button = QPushButton("Save as JSON")
        self.save_xml_button = QPushButton("Save as XML")
        self.save_mongodb_button = QPushButton("Save to MongoDB")
        
        self.save_json_button.clicked.connect(self.save_history_json)
        self.save_xml_button.clicked.connect(self.save_history_xml)
        self.save_mongodb_button.clicked.connect(self.save_history_mongodb)
        
        save_layout.addWidget(self.save_json_button)
        save_layout.addWidget(self.save_xml_button)
        save_layout.addWidget(self.save_mongodb_button)
        
        # Load buttons
        load_layout = QHBoxLayout()
        self.load_json_button = QPushButton("Load from JSON")
        self.load_xml_button = QPushButton("Load from XML")
        self.load_mongodb_button = QPushButton("Load from MongoDB")
        
        self.load_json_button.clicked.connect(self.load_history_json)
        self.load_xml_button.clicked.connect(self.load_history_xml)
        self.load_mongodb_button.clicked.connect(self.load_history_mongodb)
        
        load_layout.addWidget(self.load_json_button)
        load_layout.addWidget(self.load_xml_button)
        load_layout.addWidget(self.load_mongodb_button)
        
        layout.addLayout(save_layout)
        layout.addLayout(load_layout)
        
        group_box.setLayout(layout)
        parent_layout.addWidget(group_box)
        
    def create_playback_controls_group(self, parent_layout):
        group_box = QGroupBox("Playback Controls")
        layout = QVBoxLayout()
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Playback controls
        control_layout = QHBoxLayout()
        self.play_button = QPushButton("▶ Play")
        self.pause_button = QPushButton("⏸ Pause")
        self.stop_button = QPushButton("⏹ Stop")
        
        self.play_button.clicked.connect(self.start_playback)
        self.pause_button.clicked.connect(self.pause_playback)
        self.stop_button.clicked.connect(self.stop_playback)
        
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        
        # Speed control
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Playback Speed:"))
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(50)  # 0.5x speed
        self.speed_slider.setMaximum(200)  # 2x speed
        self.speed_slider.setValue(100)    # 1x speed (default)
        self.speed_slider.setTickInterval(25)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.valueChanged.connect(self.update_playback_speed)
        
        self.speed_label = QLabel("1.0x")
        
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        
        layout.addLayout(control_layout)
        layout.addLayout(speed_layout)
        
        # Initially disable controls (no history loaded)
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.speed_slider.setEnabled(False)
        
        group_box.setLayout(layout)
        parent_layout.addWidget(group_box)
    
    def toggle_network_settings(self, checked):
        """Enable/disable network settings based on radio button state"""
        self.network_group.setEnabled(checked)
        if self.network_game_radio.isChecked():
            self.network_options.setEnabled(True)
        else:
            self.network_options.setEnabled(False)
    
    def save_configuration(self):
        """Save the current configuration and emit signal"""
        config = self.get_current_config()
        self.config_saved.emit(config)
        self.accept()
    
    def get_current_config(self):
        """Get the current configuration as a dictionary"""
        game_mode_id = self.mode_group.checkedId()
        game_modes = ["single_player", "local_multiplayer", "network_game"]
        game_mode = game_modes[game_mode_id]

        # Network configuration
        is_host = self.host_radio.isChecked() if game_mode == "network_game" else False
        server_ip = self.ip_input.text() if game_mode == "network_game" and not is_host else ""

        config = {
            "game_mode": game_mode,
            "is_host": is_host,
            "server_ip": server_ip,
            "server_port": self.port_input.text() if game_mode == "network_game" else "",
            "date": datetime.now().isoformat()
        }

        return config
    

    
    def save_history_json(self):
        """Save game history to JSON file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save History as JSON", "", "JSON Files (*.json)"
        )
        
        if filename:
            # Get game history
            history = self.current_history
            
            try:
                self.history_manager.save_json(history, filename)
                QMessageBox.information(self, "Success", "History saved to JSON file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save history: {str(e)}")
    
    def save_history_xml(self):
        """Save game history to XML file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save History as XML", "", "XML Files (*.xml)"
        )
        
        if filename:
            # Get game history
            history = self.current_history
            
            try:
                self.history_manager.save_xml(history, filename)
                QMessageBox.information(self, "Success", "History saved to XML file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save history: {str(e)}")
    
    def save_history_mongodb(self):
        """Save game history to MongoDB"""
        # Get game history
        history = self.current_history
        
        try:
            id_str = self.history_manager.save_mongodb(history)
            if id_str:
                QMessageBox.information(self, "Success", f"History saved to MongoDB with ID: {id_str}")
            else:
                QMessageBox.warning(self, "Warning", "Failed to save to MongoDB. Check your connection.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save to MongoDB: {str(e)}")
    
    def load_history_json(self):
        """Load game history from JSON file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load History from JSON", "", "JSON Files (*.json)"
        )
        
        if filename:
            try:
                history = self.history_manager.load_json(filename)
                if history:
                    self.current_history = history
                    self._initialize_history_player()
                    self.enable_playback_controls(True)
                    QMessageBox.information(self, "Success", "History loaded from JSON file.")
                else:
                    QMessageBox.warning(self, "Warning", "Invalid or empty history file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load history: {str(e)}")
    
    def load_history_xml(self):
        """Load game history from XML file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load History from XML", "", "XML Files (*.xml)"
        )
        
        if filename:
            try:
                history = self.history_manager.load_xml(filename)
                if history:
                    self.current_history = history
                    self._initialize_history_player()
                    self.enable_playback_controls(True)
                    QMessageBox.information(self, "Success", "History loaded from XML file.")
                else:
                    QMessageBox.warning(self, "Warning", "Invalid or empty history file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load history: {str(e)}")
    
    def load_history_mongodb(self):
        """Load game history from MongoDB"""
        try:
            histories = self.history_manager.load_mongodb()
            if histories:
                # Just load the most recent history for this example
                self.current_history = histories[0]
                self._initialize_history_player()
                self.enable_playback_controls(True)
                QMessageBox.information(self, "Success", "History loaded from MongoDB.")
            else:
                QMessageBox.warning(self, "Warning", "No history found in MongoDB.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load from MongoDB: {str(e)}")
    
    def enable_playback_controls(self, enable=True):
        """Enable or disable playback controls"""
        self.play_button.setEnabled(enable)
        self.pause_button.setEnabled(False)  # Disabled until playback starts
        self.stop_button.setEnabled(False)   # Disabled until playback starts
        self.speed_slider.setEnabled(enable)
    
    def _initialize_history_player(self):
        """Initialize or reset the history player"""
        if not self.history_player:
            
            self.history_player = GameHistoryPlayer(self.scene)
            
            # Connect signals
            self.history_player.playback_progress.connect(self._update_progress)
            self.history_player.playback_finished.connect(self._on_playback_finished)
        
        # Set the current history
        self.history_player.set_history(self.current_history)
    
    def _update_progress(self, progress):
        """Update progress bar"""
        self.progress_bar.setValue(int(progress * 100))
    
    def _on_playback_finished(self):
        """Handle playback completion"""
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        QMessageBox.information(self, "Playback Complete", "Game history playback has finished.")
    
    def update_playback_speed(self):
        """Update playback speed from slider value"""
        speed_value = self.speed_slider.value() / 100.0
        self.playback_speed = speed_value
        self.speed_label.setText(f"{speed_value:.1f}x")
        
        if self.history_player:
            self.history_player.set_speed(speed_value)
    
    def start_playback(self):
        """Start playback of history"""
        if not self.current_history:
            QMessageBox.warning(self, "Warning", "No history loaded to play.")
            return
            
        if not self.history_player:
            self._initialize_history_player()
        
        # Start playback
        success = self.history_player.start()
        
        if success:
            self.play_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
        else:
            QMessageBox.warning(self, "Playback Error", "Could not start playback.")
    
    def pause_playback(self):
        """Pause playback of history"""
        if self.history_player:
            self.history_player.pause()
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
    
    def stop_playback(self):
        """Stop playback of history"""
        if self.history_player:
            self.history_player.stop()
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.progress_bar.setValue(0)
    
    def create_game_mode_group(self, parent_layout):
        group_box = QGroupBox("Game Mode")
        layout = QVBoxLayout()

        self.mode_group = QButtonGroup(self)

        self.single_player_radio = QRadioButton("Single Player")
        self.local_multiplayer_radio = QRadioButton("2 Players (Local)")
        self.network_game_radio = QRadioButton("Network Game (Online)")

        self.mode_group.addButton(self.single_player_radio, 0)
        self.mode_group.addButton(self.local_multiplayer_radio, 1)
        self.mode_group.addButton(self.network_game_radio, 2)

        # Host/Join options for network game
        self.network_options = QGroupBox("Network Options")
        network_layout = QVBoxLayout()

        self.host_radio = QRadioButton("Host Game")
        self.join_radio = QRadioButton("Join Game")
        self.network_button_group = QButtonGroup(self)
        self.network_button_group.addButton(self.host_radio, 0)
        self.network_button_group.addButton(self.join_radio, 1)
        self.host_radio.setChecked(True)

        network_layout.addWidget(self.host_radio)
        network_layout.addWidget(self.join_radio)
        self.network_options.setLayout(network_layout)
        self.network_options.setEnabled(False)

        # Default selection
        self.single_player_radio.setChecked(True)

        # Toggle network settings visibility
        self.network_game_radio.toggled.connect(self.toggle_network_settings)

        layout.addWidget(self.single_player_radio)
        layout.addWidget(self.local_multiplayer_radio)
        layout.addWidget(self.network_game_radio)
        layout.addWidget(self.network_options)

        group_box.setLayout(layout)
        parent_layout.addWidget(group_box)

    def add_internet_button(self):
        """Add a button for internet play"""
        self.internet_button = QPushButton("Internet Play Setup")
        self.internet_button.setStyleSheet("background-color: #3498db; color: white;")
        self.layout().addWidget(self.internet_button)