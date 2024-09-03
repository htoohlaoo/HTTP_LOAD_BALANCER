import socket
import requests
import random
import time
import threading
import hashlib
import signal
import sys
from rate_limiter import RateLimiter

class LoadBalancer:
    def __init__(self, port, backend_servers, status_update_callback,update_topology_callback, algorithm='round_robin',health_check_circle=4):
        self.port = port
        self.backend_servers = backend_servers
        self.healthy_servers = []
        self.lock = threading.Lock()
        self.status_update_callback = status_update_callback
        self.update_topology_callback = update_topology_callback
        self.running = True
        self.algorithm = algorithm
        self.current_index = 0  # For round robin
        self.connection_count = {server: 0 for server in backend_servers}  # For least connections
        self.server_status = {server: {'health': 'Unknown', 'requests': 0} for server in backend_servers}
        self.health_check_circle = health_check_circle
        self.rate_limiter = RateLimiter(20,10)

    def stop(self):
        self.running = False
        # Close server socket to unblock accept call if needed
        try:
            if hasattr(self, 'server_socket'):
                self.server_socket.close()
        except Exception as e:
            self.status_update_callback(f"Error closing server socket: {e}")

    def health_check(self):
        while self.running:
            with self.lock:
                for server in self.backend_servers:
                    try:
                        response = requests.get(f'http://{server[0]}:{server[1]}/health')
                        if response.status_code == 200:
                            if server not in self.healthy_servers:
                                self.healthy_servers.append(server)
                            self.server_status[server]['health'] = 'Healthy'
                            self.status_update_callback(f"Health Checking at {server[0]}:{server[1]}: OK")
                        else:
                            if server in self.healthy_servers:
                                self.healthy_servers.remove(server)
                            self.server_status[server]['health'] = 'Unhealthy'
                    except Exception as e:
                        if server in self.healthy_servers:
                            self.healthy_servers.remove(server)
                        self.server_status[server]['health'] = 'Unhealthy'
                        self.status_update_callback(f"Error checking server {server}: Connection Refused")
            self.update_topology_callback()
            time.sleep(self.health_check_circle)  # Health check interval

    def get_server_status(self):
        with self.lock:
            return dict(self.server_status)  # Return a copy of the status dictionary

    def get_server_round_robin(self):
        with self.lock:
            server = self.healthy_servers[self.current_index % len(self.healthy_servers)]
            self.current_index += 1
        return server

    def get_server_least_connections(self):
        with self.lock:
            server = min(self.healthy_servers, key=lambda s: self.connection_count[s])
        return server

    def get_server_ip_hash(self, client_ip):
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        index = hash_value % len(self.healthy_servers)
        return self.healthy_servers[index]

    def get_server_status(self):
        # Return the current status of each server
        return self.server_status

    # def handle_client(self, client_socket):
    #     request_data = client_socket.recv(1024).decode()
    #     client_ip = client_socket.getpeername()[0]

    #     if len(self.healthy_servers) <= 0:
    #         error_message = "HTTP/1.1 500 Service Unavailable\r\n\r\nNo Upstream Server Available"
    #         client_socket.sendall(error_message.encode())
    #         client_socket.close()
    #         self.status_update_callback(f"No available servers to handle the request from {client_ip}.")
    #         return

    #     # Select backend server based on the chosen algorithm
    #     if self.algorithm == 'round_robin':
    #         backend_addr = self.get_server_round_robin()
    #         self.status_update_callback(f"Selected backend server {backend_addr} using round-robin.")
    #     elif self.algorithm == 'least_connection':
    #         backend_addr = self.get_server_least_connections()
    #         self.connection_count[backend_addr] += 1  # Increment connection count for chosen server
    #         self.status_update_callback(f"Selected backend server {backend_addr} using least connections. Connection count updated.")
    #     elif self.algorithm == 'ip_hash':
    #         backend_addr = self.get_server_ip_hash(client_ip)
    #         self.status_update_callback(f"Selected backend server {backend_addr} using IP hash for client IP {client_ip}.")
    #     else:
    #         backend_addr = random.choice(self.healthy_servers)  # Default to random if unknown algorithm
    #         self.status_update_callback(f"Selected backend server {backend_addr} randomly due to unknown algorithm.")
    #     backend_socket = None
    #     try:
    #         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as backend_socket:
    #             backend_socket.connect(backend_addr)
    #             backend_socket.sendall(request_data.encode())
    #             response_data = backend_socket.recv(1024)
    #             print(response_data)
    #         client_socket.sendall(response_data)
    #         self.status_update_callback(f"Successfully forwarded request to {backend_addr} and sent response back to client IP {client_ip}.")
    #     except Exception as e:
    #         self.status_update_callback(f"Error communicating with backend server {backend_addr}")
    #     finally:
    #         client_socket.close()
    #         if(backend_socket): backend_socket.close()
    #         if self.algorithm == 'least_connection':
    #             self.connection_count[backend_addr] -= 1  # Decrement connection count after response
    #             #self.status_update_callback(f"Decremented connection count for server {backend_addr}.")

    #         if backend_addr in self.server_status:
    #             self.server_status[backend_addr]['requests'] += 1  # Increment request count for chosen server
    #             #self.status_update_callback(f"Incremented request count for server {backend_addr}. Total requests: {self.server_status[backend_addr]['requests']}.")


    def handle_client(self, client_socket):

        try:
            # Receive request data from the client
            request_data = client_socket.recv(1024).decode()
            client_ip = client_socket.getpeername()[0]
            if(self.rate_limiter.is_rate_limited(client_ip)):
                self.status_update_callback(f"IP {client_ip} exceeds rate limit")
            # Check if there are healthy servers available
            if len(self.healthy_servers) <= 0:
                error_message = "HTTP/1.1 500 Service Unavailable\r\n\r\nNo Upstream Server Available"
                client_socket.sendall(error_message.encode())
                self.status_update_callback(f"No available servers to handle the request from {client_ip}.")
                return

            # Select backend server based on the chosen algorithm
            if self.algorithm == 'round_robin':
                backend_addr = self.get_server_round_robin()
                self.status_update_callback(f"Selected backend server {backend_addr} using round-robin.")
            elif self.algorithm == 'least_connection':
                backend_addr = self.get_server_least_connections()
                self.connection_count[backend_addr] += 1  # Increment connection count for chosen server
                self.status_update_callback(f"Selected backend server {backend_addr} using least connections. Connection count updated.")
            elif self.algorithm == 'ip_hash':
                backend_addr = self.get_server_ip_hash(client_ip)
                self.status_update_callback(f"Selected backend server {backend_addr} using IP hash for client IP {client_ip}.")
            else:
                backend_addr = random.choice(self.healthy_servers)  # Default to random if unknown algorithm
                self.status_update_callback(f"Selected backend server {backend_addr} randomly due to unknown algorithm.")

            try:
                # Connect to the backend server
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as backend_socket:
                    backend_socket.connect(backend_addr)
                    backend_socket.sendall(request_data.encode())

                    # Receive the full response from the backend server
                    response_data = b""
                    while True:
                        part = backend_socket.recv(1024)
                        if not part:
                            break
                        response_data += part

                # Send the full response back to the client
                client_socket.sendall(response_data)
                self.status_update_callback(f"Successfully forwarded request to {backend_addr} and sent response back to client IP {client_ip}.")
            except Exception as e:
                self.status_update_callback(f"Error communicating with backend server {backend_addr}: {str(e)}")
        except Exception as e:
            self.status_update_callback(f"Error handling client {client_ip}: {str(e)}")
        finally:
            client_socket.close()

            # Decrement connection count for least_connection algorithm
            if self.algorithm == 'least_connection' and 'backend_addr' in locals():
                self.connection_count[backend_addr] -= 1

            # Increment request count for the chosen server
            if 'backend_addr' in locals() and backend_addr in self.server_status:
                self.server_status[backend_addr]['requests'] += 1
                self.status_update_callback(f"Incremented request count for server {backend_addr}. Total requests: {self.server_status[backend_addr]['requests']}.")



    def start_load_balancer(self):
        threading.Thread(target=self.health_check, daemon=True).start()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(('localhost', self.port))
            server_socket.listen()
            self.status_update_callback(f"Load balancer is running at port: {self.port} using {self.algorithm}...")

            while self.running:
                client_socket, _ = server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
    # def start_load_balancer(self):
    #     # Signal handler for graceful shutdown
    #     def signal_handler(sig, frame):
    #         print("Shutting down gracefully...")
    #         self.running = False
    #         self.server_socket.close()  # Properly close the server socket
    #         sys.exit(0)

    #     # Register the signal handler for SIGINT (Ctrl-C)
    #     signal.signal(signal.SIGINT, signal_handler)

    #     # Start health check thread
    #     threading.Thread(target=self.health_check, daemon=True).start()

    #     # Create server socket
    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    #         self.server_socket = server_socket

    #         # Set socket options to reuse the address
    #         server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    #         # Bind and listen
    #         server_socket.bind(('localhost', self.port))
    #         server_socket.listen()

    #         self.status_update_callback(f"Load balancer is running at port: {self.port} using {self.algorithm}...")

    #         # Accept connections in a loop
    #         while self.running:
    #             try:
    #                 client_socket, _ = server_socket.accept()
    #                 threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
    #             except OSError:
    #                 break  # Socket has been closed, exit loop

    #     print("Load balancer stopped.")