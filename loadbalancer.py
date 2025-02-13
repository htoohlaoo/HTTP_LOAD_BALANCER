import socket
import requests
import random
import time
import threading
import hashlib
import signal
import sys
from utils import get_current_ip_address
from rate_limiter import RateLimiter
import numpy as np
import joblib
import re
import urllib
import json
from sklearn.feature_extraction.text import HashingVectorizer
from ip_blocker import IPBlocker
from test_socket import test_port_binding
import urllib.parse

class LoadBalancer:
    def __init__(self, port, backend_servers, status_update_callback,update_topology_callback, algorithm='round_robin',health_check_config={"circle":3,"url":"/health"},rate_limit_config ={'limit' : 60,'period':30} ):
        self.port = port
        self.backend_servers = backend_servers
        self.healthy_servers = []
        self.lock = threading.Lock()
        self.status_update_callback = status_update_callback
        self.update_topology_callback = update_topology_callback
        self.running = False
        self.algorithm = algorithm
        self.current_index = 0  # For round robin
        self.connection_count = {server: 0 for server in backend_servers}  # For least connections
        self.server_status = {server: {'health': 'Unknown', 'requests': 0} for server in backend_servers}
        self.health_check_circle = health_check_config['circle']
        self.health_check_url = health_check_config['url']
        self.health_check_thread = None
        self.handle_thread = None
        #rate limiter configurations
        self.limit = rate_limit_config.get('limit')
        self.period = rate_limit_config.get('period')
        # self.rate_limiter = RateLimiter(redis_port=6379,limit=self.limit,period=self.period,block_period=self.block_period)
        print("Limit: ",self.limit,"    / Period :",self.period)
        self.rate_limiter = RateLimiter(rate_limit=self.limit,period=self.period)

        self.sql_detecter = joblib.load('sql_injection_model_v2.pkl')
        self.ip_blocker = IPBlocker(expiration_time=self.period)
        
    # def stop(self):
    #     self.running = False
    #     # Close server socket to unblock accept call if needed
    #     try:
    #         if hasattr(self, 'server_socket'):
    #             self.server_socket.close()
    #         self.health_check_thread.join(3)
    #         self.handle_thread.join(3)
    #         self.health_check_circle = None
    #         self.handle_thread = None
    #     except Exception as e:
    #         self.status_update_callback(f"Error closing server socket: {e}")
    def stop(self):
        try:
            self.running = False
            if hasattr(self, 'server_socket') and self.server_socket:
                try:
                    self.server_socket.shutdown(socket.SHUT_RDWR)
                except OSError as e:
                    print(f"Error shutting down socket: {e}")
                try:
                    self.server_socket.close()
                    print("Socket closed in load balancer")
                except OSError as e:
                    print(f"Error closing socket: {e}")
            if self.health_check_thread:
                print("Stopping Health Check...")
                self.health_check_thread.join(3)
            if self.handle_thread:
                self.handle_thread.join(3)
            
            try:
                self.clear_history()
                self.status_update_callback("Resetted all redis history")
            except Exception as e:
                self.status_update_callback("Error in resetting all redis history",True)

            if self.handle_thread:print("Is alive",self.handle_thread.is_alive())
            self.health_check_thread = None
            self.handle_thread = None
            self.server_status = {server: {'health': 'Unknown', 'requests': 0} for server in self.backend_servers}
            self.status_update_callback("Load balancer stopped successfully.")
           
        except Exception as e:
            self.status_update_callback(f"Error stopping threads: {e}",True)

    def health_check(self):
        while self.running:
            with self.lock:
                # print("Backend servers",self.backend_servers)
                print("Healthy servers",self.healthy_servers)
                # print('Running in health check',self.running)
                for server in self.backend_servers:
                    try:
                        response = requests.get(f'http://{server[0]}:{server[1]}{self.health_check_url}')
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
                        self.status_update_callback(f"Error checking server {server}: Connection Refused",True)
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


    
    def get_request_line(self,http_request):
        """
        Extracts the request line from a raw HTTP request string.

        Args:
            http_request (str): The full raw HTTP request.

        Returns:
            str: The request line (e.g., "GET /index.html HTTP/1.1") or None if invalid.
        """
        lines = http_request.split("\r\n")  # HTTP headers are separated by CRLF ("\r\n")
        return lines[0] if lines else None  # First line is the request line


    def extract_url_params(self,request_line):
        """
        Extracts URL query parameters from an HTTP request line.

        Args:
            request_line (str): The first line of an HTTP request (e.g., "GET /path?param1=value1&param2=value2 HTTP/1.1").

        Returns:
            dict: A dictionary of extracted query parameters.
        """
        try:
            # Split the request line to get the URL part
            parts = request_line.split(" ")
            if len(parts) < 2:
                return {}

            url = parts[1]  # Extract the path and query string (e.g., /path?param=value)
            parsed_url = urllib.parse.urlparse(url)  # Parse the URL
            query_params = urllib.parse.parse_qs(parsed_url.query)  # Extract query parameters
            
            # Convert lists to single values where applicable
            return {key: values[0] if len(values) == 1 else values for key, values in query_params.items()}
        
        except Exception as e:
            print(f"Error extracting URL parameters: {e}")
            return {}

    
    # Output: {'q': 'python', 'lang': 'en', 'page': '2'}


    def extract_http_request(self, data):
        """Extracts the HTTP request from raw socket data.

        Args:
            data: The raw socket data.

        Returns:
            The extracted HTTP request as a string, or None if extraction fails.
        """

        try:
            # Decode the raw data
            request_str = data.decode('utf-8') 

            # Extract the request line and headers
            request_lines = request_str.split('\r\n') 
            header_end = request_lines.index('') 
            request_line = request_lines[0]
            headers = request_lines[1:header_end]

            # Extract the body (if present)
            body = '\r\n'.join(request_lines[header_end + 1:]) 

            # Reconstruct the full request
            full_request = '\r\n'.join([request_line] + headers + [body])
            # print("Headers...: ",headers) 
            headers = "\r\n".join(headers) 
            return headers,body

        except (UnicodeDecodeError, ValueError, IndexError):
            # Handle potential errors (decoding, missing empty line, invalid index)
            return None

        except (UnicodeDecodeError, ValueError, IndexError):
            # Handle potential errors (decoding, missing empty line, invalid index)
            return None


    def check_request(self,sections, sql_detection_function):
        
        """
        Checks a request for SQL injection, considering headers and body.

        Args:
            request_headers: A list of header lines (e.g., ["Host: example.com", "User-Agent: ..."]).
            request_body: The request body string.
            content_type: The Content-Type header of the request.
            sql_detection_function: A function that takes a 2D array as input and returns True if it contains SQL injection patterns, False otherwise.

        Returns:
            True if the request contains SQL injection patterns, False otherwise.
        """
        # print("Checking for SQL Injection...")
        request_params = sections["request_params"]
        request_headers = sections["request_headers"]
        request_body = sections["request_body"]
        content_type = sections["content_type"]

        # Initialize the HashingVectorizer
        hashing_vectorizer = HashingVectorizer(n_features=2**12)
        if(request_params):
            print("Request Params in Check...")
            for item in request_params.values():
                print(item)
                payload = hashing_vectorizer.transform([item]).toarray()  # Vectorize and convert to numeric array
                if sql_detection_function(payload):
                    print(f"SQL Injection Detected in Request Parms: In Param : {item}",True)
                    return True


        #CHecking request params


        # List of default headers to exclude
        default_headers = [
            'Host', 'User-Agent', 'Accept', 'Accept-Language', 'Accept-Encoding',
            'Connection', 'Upgrade-Insecure-Requests', 'Content-Length', 'Content-Type','Cookie','Upgrade-Insecure-Requests','Sec-Fetch-Dest',
            'Sec-Fetch-Mode','Sec-Fetch-Site','Sec-Fetch-User','Priority'
        ]

        if isinstance(request_headers, str):
            request_headers = request_headers.splitlines()  # Convert string to list of lines
            print("Parsed Headers:", request_headers)
        for line in request_headers:
            try:
                print("Line:", line)  # Debugging Output
                if ':' not in line:  # Skip lines that don't contain ':'
                    continue
                
                key, value = line.split(':', 1)
                key, value = key.strip(), value.strip()  # Ensure clean key-value pairs
                
                if key and key not in default_headers:
                    
                    payload = hashing_vectorizer.transform([value]).toarray()  # Vectorize and convert to numeric array
                    if sql_detection_function(payload):
                        print(f"SQL Injection Detected in Header: {key} with Value: {value} in line {line}",True)
                        return True
            except ValueError:
                continue
        # print("Content-Type in check: ",content_type,'\n-----------------------------------')
        # print("Req Body in check: ",request_body)
        # Check request body based on Content-Type

        # Check request body based on Content-Type
        if content_type and re.match(r"^multipart/form-data", content_type): 
            # Extract boundary
            boundary_match = re.search(r'boundary=(.+)', content_type)
            if boundary_match:
                boundary = f"--{boundary_match.group(1)}"
                parts = request_body.split(boundary)[1:-1]  # Skip first and last boundary markers
                for part in parts:
                    if 'Content-Disposition:' in part:
                        try:
                            # Extract the payload value from Content-Disposition section
                            _, value = part.split('\r\n\r\n', 1)
                            value = value.strip('--').strip()  # Remove any trailing boundary markers
                            payload = hashing_vectorizer.transform([value]).toarray()
                            if sql_detection_function(payload):
                                print(f"SQL Injection Detected in multipart/form-data: {value}",True)
                                return True
                        except (ValueError, IndexError):
                            continue
        elif content_type and content_type == "application/x-www-form-urlencoded":
            # Decode the form data
            try:
                form_data = urllib.parse.parse_qs(request_body)  # Parse the key-value pairs into a dictionary
                print(f"Decoded Form Data: {form_data}")

                # Check each key-value pair
                for key, values in form_data.items():
                    for value in values:  # Handle cases where a key has multiple values
                        print(f"Checking Key: {key}, Value: {value}")

                        # Preprocess the value using HashingVectorizer
                        payload = hashing_vectorizer.transform([value]).toarray()
                        v = "WHERE 1=1 AND 1=1"
                        p = hashing_vectorizer.transform([v]).toarray()
                        result = sql_detection_function(p)
                        print("Testing url-encoded :",result)
                        # Check for SQL injection
                        if sql_detection_function(payload):
                            print(f"SQL Injection Detected in x-www-form-urlencoded: {key}={value}")
                            return True
            except Exception as e:
                print(f"Error processing x-www-form-urlencoded data: {e}")
        
        elif content_type and (content_type == "text/plain" or content_type == "application/json"):
            # Handle raw requests (text/plain, application/json, etc.)
            if content_type == "application/json":
                try:
                    # Parse the JSON body into a dictionary
                    json_data = json.loads(request_body)
                    print(f"Parsed JSON Data: {json_data}")

                    # Iterate over key-value pairs in the JSON
                    for key, value in json_data.items():
                        if isinstance(value, str):  # Only process string values
                            print(f"Checking Key: {key}, Value: {value}")

                            # Preprocess the value with HashingVectorizer
                            payload = hashing_vectorizer.transform([value]).toarray()
                            print(f"Preprocessed Payload for Key '{key}': {payload}")

                            # Check for SQL injection
                            if sql_detection_function(payload):
                                print(f"SQL Injection Detected in JSON: {key}={value}")
                                return True
                        else:
                            print(f"Skipping non-string value for Key: {key}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON body: {e}")
            else:
                payload = hashing_vectorizer.transform([request_body]).toarray()  # Vectorize and convert to numeric array
                v = "1' and 1 =  ( select count ( * )  from tablenames ) ; --"
                p = hashing_vectorizer.transform([v]).toarray()
                result = sql_detection_function(p)
                print("Testing text :",result)

                if sql_detection_function(payload):
                    print("SQL Injection Detected in Raw Body!")
                    return True

        print("No SQL Injection Detected.")
        return False



    def extract_content_type(self,request_data):
        """
        Extracts the Content-Type header value from the given HTTP request data.

        Args:
            request_data: The raw HTTP request data as a string.

        Returns:
            The value of the Content-Type header, or None if not found.
        """

        lines = request_data.split('\r\n')
        for line in lines:
            if line.lower().startswith('content-type:'):
                return line.split(':')[1].strip()
        return None
    
    def handle_client(self, client_socket):
        print('Request comes in...')
        print("Healthy Servers in handle",len(self.healthy_servers))
        try:
            # Receive request data from the client
            request_data = client_socket.recv(1024).decode()
            client_ip = client_socket.getpeername()[0]
            print("client_ip ",client_ip)
            
            if(self.ip_blocker.is_blocked(client_ip)):
                print('Not Permitted... | Blocked! ')
                error_message = "HTTP/1.1 403 Forbidden\r\n\r\nRequest Forbidden"
                client_socket.sendall(error_message.encode())
                self.status_update_callback(f"Request from {client_ip} forbidden. ( Blocked )",danger_alert=True)
                return

            if(self.rate_limiter.is_rate_limited(client_ip)):
                print('Not Permitted... | rate limited')
                error_message = "HTTP/1.1 403 Forbidden\r\n\r\nRequest Forbidden"
                client_socket.sendall(error_message.encode())
                self.status_update_callback(f"Request from {client_ip} forbidden. ( Rate limited! )",danger_alert=True)
                self.ip_blocker.block_ip(client_ip)
                return
           
            print("Request Data",request_data)
            headers,body = self.extract_http_request(request_data.encode('utf-8'))
            content_type = self.extract_content_type(request_data)
            request_line = self.get_request_line(request_data)
            print("Request Line",request_line)
            request_params = self.extract_url_params(request_line)
            print("Request Params",request_params)
            sections = {
                "request_params":request_params,
                "request_headers":headers,
                "request_body":body,
                "content_type":content_type,
            }
            if(self.check_request(sections,self.sql_detecter.predict)):
                self.status_update_callback(f"SQL Injection Detected from IP : {client_ip}",danger_alert=True)
                print('Not Permitted... | SQLi detected')
                error_message = "HTTP/1.1 403 Forbidden\r\n\r\nRequest Forbidden"
                client_socket.sendall(error_message.encode())
                self.status_update_callback(f"Request from {client_ip} forbidden. ( SQL Injection Detected! )",danger_alert=True)
                self.ip_blocker.block_ip(client_ip)
                return
            
            # Check if there are healthy servers available
            if len(self.healthy_servers) <= 0:
                error_message = "HTTP/1.1 500 Service Unavailable\r\n\r\nNo Upstream Server Available"
                client_socket.sendall(error_message.encode())
                self.status_update_callback(f"No available servers to handle the request from {client_ip}.",danger_alert=True)
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
                self.status_update_callback(f"Error communicating with backend server {backend_addr}: {str(e)}",danger_alert=True)
        except Exception as e:
            self.status_update_callback(f"Error handling client {client_ip}: {str(e)}",danger_alert=True)
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
        print("Starting load balancer...")
        self.running = True
        self.health_check_thread = threading.Thread(target=self.health_check, daemon=True)
        self.health_check_thread.start()
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.server_socket:
            # Allow socket address reuse
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            machine_ip = get_current_ip_address()
            if not machine_ip:
                machine_ip = '127.0.0.1'
            machine_ip = '127.0.0.1'
            try:
                self.server_socket.bind((machine_ip, self.port))
                self.server_socket.listen()
            
                self.status_update_callback(f"Load balancer is running at ip {machine_ip} port: {self.port} using {self.algorithm}...")
                print(self.running,'Running')
                while self.running:
                    print("Before running socket")
                    try:
                        client_socket, _ = self.server_socket.accept()
                        self.handle_thread = threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True)
                        self.handle_thread.start()
                        print("After running socket")
                    except OSError as e:
                        if not self.running:
                            # This error is expected when stopping the load balancer
                            print("Load balancer stopped, exiting accept loop.")
                        else:
                            self.status_update_callback(f"Socket error in handling: {e}",True)
                        break
            except OSError as e:    
                        self.stop()
                        self.status_update_callback(f"Socket error: {e}",True)
    def clear_history(self):
        self.rate_limiter.clear_rate_limiter()
        self.ip_blocker.clear_block()
    