import socket
import threading
import json
import time
from PySide6.QtCore import QObject, Signal, Slot, QTimer
import netaddr
class GameNetworkEvent:
    """Network event types for tower defense game"""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PLACE_TOWER = "place_tower"
    START_WAVE = "start_wave"
    ENEMY_KILLED = "enemy_killed"
    GAME_OVER = "game_over"
    SYNC_STATE = "sync_state"
    TOWER_UPGRADE = "tower_upgrade"
    TOWER_SELL = "tower_sell"
    CHAT_MESSAGE = "chat_message"
    SPAWN_ENEMY = "spawn_enemy"

class NetworkManager(QObject):
    """Manages network communication for multiplayer games"""
    
    # Signals for game events
    connected = Signal(str)  # Player ID
    disconnected = Signal()
    error = Signal(str)
    event_received = Signal(dict)
    player_joined = Signal(str)  # Player ID
    player_left = Signal(str)    # Player ID
    state_request = Signal()  # Request for game state
    def __init__(self, is_host=False):
        super().__init__()
        self.socket = None
        self.server_address = None
        self.player_id = None
        self.is_host = is_host
        self.connected_players = []
        self.server_thread = None
        self.client_thread = None
        self.running = False
        
        # For host-specific data
        self.server_socket = None
        self.clients = {}
        
        self.connection_status = "disconnected"
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._send_heartbeat)
        self.heartbeat_timer.setInterval(5000)  # 5 seconds
        
    def host_game(self, port=5555):
        """Host a new game server"""
        try:
            self.is_host = True
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(2)  # Allow 2 players max
            
            print(f"Server started on 127.0.0.1:{port}")

            self.player_id = "host"
            self.connected_players.append(self.player_id)
            
            # Start server thread
            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Emit connected signal
            self.connected.emit(self.player_id)
            
            return True
        except Exception as e:
            self.error.emit(f"Failed to host game: {str(e)}")
            return False
    
    def join_game(self, address, port=5555):
        """Join an existing game"""
        try:
            # Sanitize the address input
            if not address or address.strip() == "":
                address = "127.0.0.1"  # Default to localhost
                
            print(f"Attempting to connect to {address}:{port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            address = str(netaddr.IPAddress(address,flags= netaddr.ZEROFILL))  
            self.server_address = (address, port)
            self.socket.settimeout(5)  # Add timeout to prevent hanging
            self.socket.connect(self.server_address)
            self.socket.settimeout(None)  # Reset timeout for normal operations

            # Send initial connection message
            self.socket.sendall(json.dumps({
                "type": GameNetworkEvent.CONNECT,
                "data": {"player_name": "Player"}
            }).encode('utf-8'))
            
            # Receive player ID from server
            data = self.socket.recv(4096).decode('utf-8')
            response = json.loads(data)
            
            if response["type"] == GameNetworkEvent.CONNECT:
                self.player_id = response["data"]["player_id"]
                self.connected_players = response["data"]["players"]
                
                # Start client thread
                self.running = True
                self.client_thread = threading.Thread(target=self._client_loop)
                self.client_thread.daemon = True
                self.client_thread.start()
                
                # Emit connected signal
                self.connected.emit(self.player_id)
                
                return True
            else:
                self.error.emit("Invalid server response")
                return False
                
        except socket.timeout:
            self.error.emit(f"Connection timed out - server not responding")
            return False
        except ConnectionRefusedError:
            self.error.emit(f"Connection refused - make sure the server is running")
            return False
        except Exception as e:
            self.error.emit(f"Failed to join game: {str(e)}")
            print(f"Client error: {str(e)}")  # Add detailed logging
            return False
    
    def disconnect(self):
        """Disconnect from the game"""
        self.running = False
        
        if self.is_host and self.server_socket:
            try:
                # Notify clients about shutdown
                self._broadcast({
                    "type": GameNetworkEvent.DISCONNECT,
                    "data": {"reason": "Host disconnected"}
                })
                
                # Close all client connections
                for client_socket in self.clients.values():
                    client_socket.close()
                
                self.server_socket.close()
            except:
                pass
        
        if self.socket:
            try:
                # Send disconnect message
                self.socket.sendall(json.dumps({
                    "type": GameNetworkEvent.DISCONNECT,
                    "data": {"player_id": self.player_id}
                }).encode('utf-8'))
                
                self.socket.close()
            except:
                pass
        
        self.disconnected.emit()
    def send_game_state(self, state_data):
        """Send the current game state to all connected clients"""
        event = {
            "type": GameNetworkEvent.SYNC_STATE,
            "data": state_data,
            "player_id": self.player_id,
            "timestamp": time.time()
        }

        if self.is_host:
            self._broadcast(event)
    def send_event(self, event_type, data):
        """Send a game event to the server/clients"""
        event = {
            "type": event_type,
            "data": data,
            "player_id": self.player_id,
            "timestamp": time.time()
        }
        
        if self.is_host:
            # Process event locally and broadcast to clients
            self._handle_event(event)
            self._broadcast(event)
        else:
            # Send event to server
            if self.socket:
                try:
                    self.socket.sendall(json.dumps(event).encode('utf-8'))
                except Exception as e:
                    self.error.emit(f"Failed to send event: {str(e)}")
    
    def _server_loop(self):
        """Main loop for the server"""
        print("Server started, waiting for players...")
        
        while self.running:
            try:
                # Accept new client connection
                client_socket, address = self.server_socket.accept()
                print(f"New connection from {address}")
                
                # Handle client registration
                data = client_socket.recv(4096).decode('utf-8')
                event = json.loads(data)
                
                if event["type"] == GameNetworkEvent.CONNECT:
                    # Assign player ID (for now, just "player2")
                    player_id = "player2"
                    self.clients[player_id] = client_socket
                    self.connected_players.append(player_id)
                    
                    # Send confirmation with player ID
                    client_socket.sendall(json.dumps({
                        "type": GameNetworkEvent.CONNECT,
                        "data": {
                            "player_id": player_id,
                            "players": self.connected_players
                        }
                    }).encode('utf-8'))
                    
                    # Notify about new player
                    self.player_joined.emit(player_id)
                    
                    # Start thread to handle this client
                    thread = threading.Thread(target=self._handle_client, args=(client_socket, player_id))
                    thread.daemon = True
                    thread.start()
            except Exception as e:
                if self.running:  # Only show error if not deliberately shutting down
                    print(f"Server error: {str(e)}")
    
    def _handle_client(self, client_socket, player_id):
        """Handle communication with a specific client"""
        try:
            while self.running:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                event = json.loads(data)
                event["player_id"] = player_id  # Ensure correct player_id
                
                # On initial connection, send game state
                if event["type"] == GameNetworkEvent.CONNECT:
                    # Request the current game state from the host
                    self.state_request.emit()
                
                # Process the event
                self._handle_event(event)
                
                # Forward to other clients
                self._broadcast(event, exclude=player_id)
                
        except Exception as e:
            print(f"Error handling client {player_id}: {str(e)}")
        finally:
            # Handle disconnection
            if player_id in self.clients:
                self.clients[player_id].close()
                del self.clients[player_id]
                self.connected_players.remove(player_id)
                self.player_left.emit(player_id)
    
    def _client_loop(self):
        """Main loop for the client"""
        try:
            while self.running:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                event = json.loads(data)
                
                # Handle disconnect event
                if event["type"] == GameNetworkEvent.DISCONNECT:
                    self.running = False
                    self.disconnected.emit()
                    break
                
                # Process the event
                self._handle_event(event)
                
        except Exception as e:
            if self.running:  # Only show error if not deliberately shutting down
                self.error.emit(f"Network error: {str(e)}")
                self.disconnected.emit()
    
    def _broadcast(self, event, exclude=None):
        """Broadcast an event to all connected clients except excluded one"""
        data = json.dumps(event).encode('utf-8')
        
        for player_id, client_socket in self.clients.items():
            if player_id != exclude:
                try:
                    client_socket.sendall(data)
                except:
                    pass  # Will be handled by client handler thread
    
    def _handle_event(self, event):
        """Process a game event"""
        # Emit the event for game logic to handle
        self.event_received.emit(event)
        
    def _send_heartbeat(self):
        """Send heartbeat to check connection status"""
        if not self.running:
            return
            
        if self.is_host:
            # Check if clients are still connected
            dead_clients = []
            for player_id, client_socket in self.clients.items():
                try:
                    # Non-blocking check
                    client_socket.setblocking(0)
                    # Try to peek at the socket buffer
                    data = client_socket.recv(16, socket.MSG_PEEK)
                    if not data:
                        dead_clients.append(player_id)
                    client_socket.setblocking(1)
                except:
                    pass
                
            # Remove dead connections
            for player_id in dead_clients:
                self.player_left.emit(player_id)
                self.clients[player_id].close()
                del self.clients[player_id]
                self.connected_players.remove(player_id)
                
        else:
            # Client sends heartbeat to server
            try:
                self.send_event("heartbeat", {})
            except:
                # Connection may be lost, try to reconnect
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.reconnect_attempts += 1
                    self.connection_status = "reconnecting"
                    self.error.emit(f"Connection lost. Attempting to reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts})...")
                    
                    # Try to reconnect
                    try:
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.socket.settimeout(5)
                        self.socket.connect(self.server_address)
                        self.socket.settimeout(None)
                        
                        # Reconnection successful
                        self.reconnect_attempts = 0
                        self.connection_status = "connected"
                        self.error.emit("Reconnected to server!")
                        
                        # Re-register with server
                        self.socket.sendall(json.dumps({
                            "type": GameNetworkEvent.CONNECT,
                            "data": {"player_name": "Player", "reconnect": True}
                        }).encode('utf-8'))
                        
                    except:
                        pass  # Will try again on next heartbeat
                else:
                    # Give up after max attempts
                    self.connection_status = "disconnected"
                    self.running = False
                    self.disconnected.emit()
                    self.error.emit("Failed to reconnect after multiple attempts. Connection closed.")