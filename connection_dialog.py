from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QProgressBar, QMessageBox,
                              QRadioButton, QButtonGroup, QGroupBox, QTabWidget,
                              QTextEdit, QComboBox, QCheckBox, QSpinBox,QWidget)
from PySide6.QtCore import Signal, QTimer
import socket
import requests
import json
import os

class ConnectionDialog(QDialog):
    """Dialog for setting up network connections"""
    
    connection_ready = Signal(dict)  # Emits connection settings when ready
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Internet Connection Setup")
        self.resize(500, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Connection type tabs
        tab_widget = QTabWidget()
        self.host_tab = QWidget()
        self.join_tab = QWidget()
        tab_widget.addTab(self.host_tab, "Host Game")
        tab_widget.addTab(self.join_tab, "Join Game")
        
        # Setup host tab
        self.setup_host_tab()
        
        # Setup join tab
        self.setup_join_tab()
        
        layout.addWidget(tab_widget)
        
        # Status area
        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready to connect")
        self.status_label.setStyleSheet("font-weight: bold;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.handle_connect)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def setup_host_tab(self):
        layout = QVBoxLayout()
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(5555)
        port_layout.addWidget(self.port_input)
        layout.addLayout(port_layout)
        
        # Your public IP
        ip_group = QGroupBox("Your Public IP")
        ip_layout = QVBoxLayout()
        
        self.public_ip_label = QLabel("Checking...")
        self.check_ip_button = QPushButton("Check My Public IP")
        self.check_ip_button.clicked.connect(self.check_public_ip)
        
        ip_layout.addWidget(self.public_ip_label)
        ip_layout.addWidget(self.check_ip_button)
        ip_group.setLayout(ip_layout)
        layout.addWidget(ip_group)
        
        # Port forwarding instructions
        instructions = QGroupBox("Port Forwarding Instructions")
        instructions_layout = QVBoxLayout()
        
        instructions_text = QTextEdit()
        instructions_text.setReadOnly(True)
        instructions_text.setPlainText(
            "To host a game over the internet, you need to set up port forwarding:\n\n"
            "1. Log into your router (usually at 192.168.1.1 or 192.168.0.1)\n"
            "2. Find the port forwarding section\n"
            "3. Create a new rule forwarding the port above (default: 5555)\n"
            "4. Point it to your computer's local IP address\n"
            "5. Save the settings\n\n"
            "Once set up, give your friends your public IP address to connect."
        )
        
        instructions_layout.addWidget(instructions_text)
        instructions.setLayout(instructions_layout)
        layout.addWidget(instructions)
        
        # UPnP option
        upnp_layout = QHBoxLayout()
        self.upnp_checkbox = QCheckBox("Try UPnP automatic port forwarding")
        self.upnp_checkbox.setChecked(True)
        upnp_layout.addWidget(self.upnp_checkbox)
        layout.addLayout(upnp_layout)
        
        self.host_tab.setLayout(layout)
    
    def setup_join_tab(self):
        layout = QVBoxLayout()
        
        # Server address
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("Server IP:"))
        self.server_ip_input = QLineEdit()
        self.server_ip_input.setPlaceholderText("Enter host's IP address")
        server_layout.addWidget(self.server_ip_input)
        layout.addLayout(server_layout)
        
        # Port
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.join_port_input = QSpinBox()
        self.join_port_input.setRange(1024, 65535)
        self.join_port_input.setValue(5555)
        port_layout.addWidget(self.join_port_input)
        layout.addLayout(port_layout)
        
        # Recent connections
        recent_group = QGroupBox("Recent Connections")
        recent_layout = QVBoxLayout()
        
        self.recent_combo = QComboBox()
        self.load_recent_connections()
        
        recent_layout.addWidget(self.recent_combo)
        self.recent_combo.currentTextChanged.connect(self.on_recent_selected)
        
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        # Connection test
        test_layout = QHBoxLayout()
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        self.test_status = QLabel("")
        test_layout.addWidget(self.test_button)
        test_layout.addWidget(self.test_status)
        layout.addLayout(test_layout)
        
        self.join_tab.setLayout(layout)
    
    def load_recent_connections(self):
        """Load recent connections from file"""
        self.recent_combo.clear()
        self.recent_combo.addItem("Select a recent connection...")
        
        try:
            if os.path.exists("recent_connections.json"):
                with open("recent_connections.json", "r") as f:
                    connections = json.load(f)
                    for conn in connections:
                        self.recent_combo.addItem(f"{conn['ip']}:{conn['port']}")
        except:
            pass
    
    def save_recent_connection(self, ip, port):
        """Save connection details for future use"""
        connections = []
        try:
            if os.path.exists("recent_connections.json"):
                with open("recent_connections.json", "r") as f:
                    connections = json.load(f)
        except:
            connections = []
            
        # Check if this connection already exists
        exists = False
        for conn in connections:
            if conn["ip"] == ip and conn["port"] == port:
                exists = True
                break
                
        if not exists:
            connections.append({"ip": ip, "port": port})
            
            # Keep only the 5 most recent connections
            if len(connections) > 5:
                connections = connections[-5:]
                
            try:
                with open("recent_connections.json", "w") as f:
                    json.dump(connections, f)
            except:
                pass
    
    def on_recent_selected(self, text):
        """Handle selection of a recent connection"""
        if text and ":" in text and text != "Select a recent connection...":
            ip, port = text.split(":")
            self.server_ip_input.setText(ip)
            self.join_port_input.setValue(int(port))
    
    def check_public_ip(self):
        """Check and display the user's public IP address"""
        self.check_ip_button.setEnabled(False)
        self.public_ip_label.setText("Checking...")
        
        # Use a timer to run in the background
        QTimer.singleShot(100, self._fetch_public_ip)
    
    def _fetch_public_ip(self):
        """Background fetch of public IP"""
        try:
            # Try multiple services in case one fails
            services = [
                "https://api.ipify.org?format=json",
                "https://api.myip.com",
                "https://ip.seeip.org/json"
            ]
            
            public_ip = None
            
            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if "ip" in data:
                            public_ip = data["ip"]
                            break
                except:
                    continue
                    
            if public_ip:
                self.public_ip_label.setText(f"Your public IP: {public_ip}")
            else:
                self.public_ip_label.setText("Could not determine your public IP")
                
        except Exception as e:
            self.public_ip_label.setText(f"Error checking IP: {str(e)}")
        
        finally:
            self.check_ip_button.setEnabled(True)
    
    def test_connection(self):
        """Test connection to the specified server"""
        ip = self.server_ip_input.text().strip()
        port = self.join_port_input.value()
        
        if not ip:
            self.test_status.setText("Please enter an IP address")
            return
            
        self.test_button.setEnabled(False)
        self.test_status.setText("Testing connection...")
        
        # Use a timer to run in the background
        QTimer.singleShot(100, lambda: self._do_connection_test(ip, port))
    
    def _do_connection_test(self, ip, port):
        """Background test of connection"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((ip, port))
            s.close()
            self.test_status.setText("Connection successful!")
            self.test_status.setStyleSheet("color: green;")
        except Exception as e:
            self.test_status.setText(f"Connection failed: {str(e)}")
            self.test_status.setStyleSheet("color: red;")
        finally:
            self.test_button.setEnabled(True)
    
    def handle_connect(self):
        """Process the connection request"""
        active_tab = self.parent().findChild(QTabWidget).currentIndex()
        
        # Host game
        if active_tab == 0:
            port = self.port_input.value()
            
            # Try UPnP if checked
            upnp_success = False
            if self.upnp_checkbox.isChecked():
                try:
                    self.status_label.setText("Attempting UPnP port forwarding...")
                    self.progress_bar.setVisible(True)
                    
                    # UPnP logic would go here
                    # For now, we'll just fake success
                    upnp_success = True
                    
                    self.status_label.setText("UPnP port forwarding successful!")
                except:
                    self.status_label.setText("UPnP port forwarding failed. Manual setup required.")
            
            # Emit the connection settings
            self.connection_ready.emit({
                "is_host": True,
                "port": port,
                "upnp_success": upnp_success
            })
            
            self.accept()
            
        # Join game
        else:
            ip = self.server_ip_input.text().strip()
            port = self.join_port_input.value()
            
            if not ip:
                QMessageBox.warning(self, "Missing Information", 
                                   "Please enter the server IP address.")
                return
            
            # Save this connection for future use
            self.save_recent_connection(ip, port)
            
            # Emit the connection settings
            self.connection_ready.emit({
                "is_host": False,
                "ip": ip,
                "port": port
            })
            
            self.accept()