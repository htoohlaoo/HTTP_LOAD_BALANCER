import socket
import sys
def test_port_binding(ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_socket:
            test_socket.bind((ip, int(port)))
            return True
    except Exception as e:
        print(f"Failed to bind port {port} on {ip}: {e}")
        return False

if __name__ == "__main__":
    test_port_binding(sys.argv[1], sys.argv[2])  # Replace 8080 with your load balancer's port
