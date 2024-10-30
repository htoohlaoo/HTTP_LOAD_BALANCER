import os
import psutil
import socket

def clear_port(port):
    # Find the process using the specified port
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port:
            pid = conn.pid
            if pid is not None:
                try:
                    # Terminate the process
                    p = psutil.Process(pid)
                    p.terminate()  # Or you can use p.kill() for a more forceful kill
                    p.wait(timeout=3)
                    print(f"Process {pid} on port {port} terminated successfully.")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                    print(f"Error terminating process: {e}")
            else:
                print(f"No process found using port {port}.")
            return

    print(f"No process found using port {port}.")


def get_current_ip_address():
    try:
        # Connect to an external server (Google's public DNS) to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        # This doesn't actually connect, but the OS will choose the appropriate IP address
        s.connect(('8.8.8.8', 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        return None
