import socket
import threading
import miniupnpc

class UPnPHelper:
    """Helper class for UPnP port forwarding"""
    
    def __init__(self):
        self.upnp = None
        self.mapped_ports = []
        
    def discover(self):
        """Discover UPnP devices on the network"""
        try:
            self.upnp = miniupnpc.UPnP()
            self.upnp.discoverdelay = 200  # Milliseconds
            
            # Discover devices
            devices = self.upnp.discover()
            if devices == 0:
                return False
                
            # Select first IGD (Internet Gateway Device)
            self.upnp.selectigd()
            return True
            
        except Exception as e:
            print(f"UPnP discovery error: {str(e)}")
            return False
    
    def add_port_mapping(self, port, protocol="TCP", description="Tower Defense Game"):
        """Map an external port to the local machine"""
        if not self.upnp:
            if not self.discover():
                return False
        
        try:
            # Get the local IP
            local_ip = socket.gethostbyname(socket.gethostname())
            
            # Add port mapping
            result = self.upnp.addportmapping(
                port,               # External port
                protocol,           # Protocol
                local_ip,           # Internal host
                port,               # Internal port
                description,        # Description
                ''                  # Remote host (empty for any)
            )
            
            if result:
                self.mapped_ports.append((port, protocol))
                return True
            return False
            
        except Exception as e:
            print(f"UPnP port mapping error: {str(e)}")
            return False
    
    def remove_port_mapping(self, port, protocol="TCP"):
        """Remove a port mapping"""
        if not self.upnp:
            return False
            
        try:
            self.upnp.deleteportmapping(port, protocol)
            if (port, protocol) in self.mapped_ports:
                self.mapped_ports.remove((port, protocol))
            return True
        except:
            return False
    
    def cleanup(self):
        """Remove all port mappings created by this instance"""
        if not self.upnp:
            return
            
        for port, protocol in list(self.mapped_ports):
            self.remove_port_mapping(port, protocol)