import socket
import requests
import random
import time
import threading
import socket
import threading
import time
import random
import requests
import hashlib

class LoadBalancer:
    def __init__(self, port, backend_servers, status_update_callback, algorithm='round_robin'):
        self.port = port
        self.backend_servers = backend_servers
        self.healthy_servers = []
        self.lock = threading.Lock()
        self.status_update_callback = status_update_callback
        self.running = True
        self.algorithm = algorithm
        self.current_index = 0  # For round robin
        self.connection_count = {server: 0 for server in backend_servers}  # For least connections

    def stop(self):
        self.running = False
        # Close server socket to unblock accept call if needed
        try:
            if hasattr(self, 'server_socket'):
                self.server_socket.close()
        except Exception as e:
            self.status_update_callback(f"Error closing server socket: {e}")

    def health_check(self):
        print('Checking servers...')
        while self.running:
            with self.lock:
                for server in self.backend_servers:
                    try:
                        response = requests.get(f'http://{server[0]}:{server[1]}/health')
                        if response.status_code == 200:
                            if server not in self.healthy_servers:
                                self.healthy_servers.append(server)
                            self.status_update_callback(f"{server[0]} checking at port {server[1]}: OK")
                        else:
                            if server in self.healthy_servers:
                                self.healthy_servers.remove(server)
                    except Exception as e:
                        if server in self.healthy_servers:
                            self.healthy_servers.remove(server)
                        self.status_update_callback(f"Error during check for server {server}: {e}")

            time.sleep(3)  # Health check interval
    
    def get_server_round_robin(self):
        with self.lock:
            server = self.healthy_servers[self.current_index % len(self.healthy_servers)]
            self.current_index += 1
        return server
    
    def get_server_least_connections(self):
        with self.lock:
            # Select server with minimum active connections
            server = min(self.healthy_servers, key=lambda s: self.connection_count[s])
        return server

    def get_server_ip_hash(self, client_ip):
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        index = hash_value % len(self.healthy_servers)
        return self.healthy_servers[index]
    
    def handle_client(self, client_socket):
        request_data = client_socket.recv(1024).decode()
        client_ip = client_socket.getpeername()[0]

        if len(self.healthy_servers) <= 0:
            client_socket.sendall(b"HTTP/1.1 500 Service is unavailable\r\n\r\nNo Upstream Server Available")
            client_socket.close()
            return

        # Select backend server based on the chosen algorithm
        if self.algorithm == 'round_robin':
            backend_addr = self.get_server_round_robin()
        elif self.algorithm == 'least_connection':
            backend_addr = self.get_server_least_connections()
            self.connection_count[backend_addr] += 1  # Increment connection count for chosen server
        elif self.algorithm == 'ip_hash':
            backend_addr = self.get_server_ip_hash(client_ip)
        else:
            backend_addr = random.choice(self.healthy_servers)  # Default to random if unknown algorithm

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as backend_socket:
                backend_socket.connect(backend_addr)
                backend_socket.sendall(request_data.encode())
                response_data = backend_socket.recv(1024)

            client_socket.sendall(response_data)
        except Exception as e:
            self.status_update_callback(f"Error communicating with backend server {backend_addr}: {e}")
        finally:
            client_socket.close()
            if self.algorithm == 'least_connection':
                self.connection_count[backend_addr] -= 1  # Decrement connection count after response

    def start_load_balancer(self):
        threading.Thread(target=self.health_check).start()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(('localhost', self.port))
            server_socket.listen()
            self.status_update_callback(f"Load balancer is running at port: {self.port} ...")

            while self.running:
                client_socket, _ = server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
