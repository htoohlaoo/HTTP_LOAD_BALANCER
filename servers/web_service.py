import json
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

class RequestCounterHandler(BaseHTTPRequestHandler):
    request_count = 0

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response_content = { "status": "healthy" }
            json_response = json.dumps(response_content)
            self.wfile.write(json_response.encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            RequestCounterHandler.request_count += 1
            response_content = { "count": RequestCounterHandler.request_count }
            json_response = json.dumps(response_content)
            self.wfile.write(json_response.encode('utf-8'))

def run(server_class=HTTPServer, handler_class=RequestCounterHandler, ip='127.0.0.1', port=8080):
    server_address = (ip, port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on {ip}:{port}...')
    httpd.serve_forever()

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Simple Python HTTP Server with Request Counter')
    parser.add_argument('--ip', type=str, default='127.0.0.1', help='IP address to bind the server to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind the server to (default: 8080)')
    args = parser.parse_args()
    
    # Run the server with provided IP and port
    run(ip=args.ip, port=args.port)
