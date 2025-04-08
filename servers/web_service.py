import json
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

class RequestCounterHandler(BaseHTTPRequestHandler):
    request_count = 0
    server_name = "Unnamed"  # Default name

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response_content = { "status": "healthy", "name": self.server_name }
            self.wfile.write(json.dumps(response_content).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            RequestCounterHandler.request_count += 1
            response_content = {
                "count": RequestCounterHandler.request_count,
                "name": self.server_name
            }
            self.wfile.write(json.dumps(response_content).encode('utf-8'))

    @property
    def server_name(self):
        return self.server.server_name_custom


def run(server_class=HTTPServer, handler_class=RequestCounterHandler, ip='127.0.0.1', port=8080, name="Unnamed"):
    server_address = (ip, port)
    httpd = server_class(server_address, handler_class)
    httpd.server_name_custom = name
    print(f'Starting httpd server on {ip}:{port} with name "{name}"...')
    httpd.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple Python HTTP Server with Request Counter')
    parser.add_argument('--ip', type=str, default='127.0.0.1', help='IP address to bind the server to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind the server to')
    parser.add_argument('--name', type=str, default='Unnamed', help='Name of the server')

    args = parser.parse_args()
    
    run(ip=args.ip, port=args.port, name=args.name)
#Run with the following command
#python3 server.py --ip 127.0.0.1 --port 8081 --name ServerA
