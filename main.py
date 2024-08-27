import tkinter as tk
from tkinter import ttk
import json
import threading
from loadbalancer import LoadBalancer
import datetime
from logger import Logger
class LoadBalancerUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HTTP Load Balancer")
        self.geometry("600x400")

        # Server List Section
        self.server_frame = ttk.LabelFrame(self, text="Server List")
        self.server_frame.pack(fill="both", padx=10, pady=10, expand=True)

        # Server Listbox
        self.server_listbox = tk.Listbox(self.server_frame, height=8)
        self.server_listbox.pack(side="left", fill="both", padx=10, pady=10, expand=True)

        # Server List Scrollbar
        self.scrollbar = tk.Scrollbar(self.server_frame, orient="vertical")
        self.scrollbar.config(command=self.server_listbox.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.server_listbox.config(yscrollcommand=self.scrollbar.set)

        # Canvas for Topology
        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(fill="both", padx=10, pady=10, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="white")
        self.canvas.pack(fill="both", expand=True)

        # Add/Remove Server Buttons
        button_frame = ttk.Frame(self.server_frame)
        button_frame.pack(side="left", padx=10, pady=5)

        self.add_server_button = ttk.Button(button_frame, text="Add Server", command=self.show_add_server_form)
        self.add_server_button.pack(side="left", padx=5)

        self.remove_server_button = ttk.Button(button_frame, text="Remove Server", command=self.remove_server)
        self.remove_server_button.pack(side="left", padx=5)

        # Load Balancer Control Section
        self.control_frame = ttk.LabelFrame(self, text="Load Balancer Control")
        self.control_frame.pack(fill="x", padx=10, pady=10)
        # Algorithm Selection
        ttk.Label(self.control_frame, text="Select Algorithm:").pack(side="left", padx=10)
        self.algorithm_var = tk.StringVar()
        self.algorithm_combobox = ttk.Combobox(
            self.control_frame, 
            textvariable=self.algorithm_var, 
            values=["Round Robin", "Least Connections", "IP Hash"]
        )
        self.algorithm_combobox.current(0)  # Set default to "Round Robin"
        self.algorithm_combobox.pack(side="left", padx=10, pady=5)

        # Start/Stop Buttons
        self.start_button = ttk.Button(self.control_frame, text="Start Load Balancer", command=self.start_load_balancer)
        self.start_button.pack(side="left", padx=10, pady=5)

        self.stop_button = ttk.Button(self.control_frame, text="Stop Load Balancer", command=self.stop_load_balancer)
        self.stop_button.pack(side="left", padx=10, pady=5)

        # Status Label
        self.status_label = ttk.Label(self.control_frame, text="Status: Stopped")
        self.status_label.pack(side="left", padx=20, pady=5)

        # Logs/Status Section
        self.log_frame = ttk.LabelFrame(self, text="Logs")
        self.log_frame.pack(fill="both", padx=10, pady=10, expand=True)

        self.log_text = tk.Text(self.log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", padx=10, pady=10, expand=True)

        self.load_balancer = None
        self.load_balancer_thread = None
        self.logger = Logger(self.log_text)

        self.load_servers_from_json()

        # Bind the canvas resize event to update topology
        self.canvas.bind("<Configure>", lambda event: self.update_topology())

    def save_servers_to_json(self):
        servers = []
        for i in range(self.server_listbox.size()):
            server_entry = self.server_listbox.get(i)
            name, ip_port = server_entry.split(' (')
            ip, port = ip_port.rstrip(')').split(':')
            servers.append({"name": name, "ip": ip, "port": int(port)})
        
        with open('servers.json', 'w') as f:
            json.dump(servers, f, indent=4)

    def load_servers_from_json(self):
        try:
            with open('servers.json', 'r') as f:
                servers = json.load(f)
                for server in servers:
                    server_entry = f"{server['name']} ({server['ip']}:{server['port']})"
                    self.server_listbox.insert(tk.END, server_entry)
        except FileNotFoundError:
            # No previous server list, so nothing to load
            pass

    def show_add_server_form(self):
        # Create a new Toplevel window
        self.add_server_window = tk.Toplevel(self)
        self.add_server_window.title("Add New Server")
        self.add_server_window.geometry("300x250")

        # Server Name
        tk.Label(self.add_server_window, text="Server Name:").pack(padx=10, pady=5)
        self.server_name_entry = ttk.Entry(self.add_server_window)
        self.server_name_entry.pack(padx=10, pady=5)

        # Server IP
        tk.Label(self.add_server_window, text="Server IP:").pack(padx=10, pady=5)
        self.server_ip_entry = ttk.Entry(self.add_server_window)
        self.server_ip_entry.pack(padx=10, pady=5)

        # Server Port
        tk.Label(self.add_server_window, text="Server Port:").pack(padx=10, pady=5)
        self.server_port_entry = ttk.Entry(self.add_server_window)
        self.server_port_entry.pack(padx=10, pady=5)

        # Confirm and Cancel Buttons
        button_frame = ttk.Frame(self.add_server_window)
        button_frame.pack(pady=10)

        confirm_button = ttk.Button(button_frame, text="Confirm", command=self.add_server)
        confirm_button.pack(side="left", padx=10)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.add_server_window.destroy)
        cancel_button.pack(side="left", padx=10)

    def add_server(self):
        server_name = self.server_name_entry.get()
        server_ip = self.server_ip_entry.get()
        server_port = self.server_port_entry.get()
        
        if server_name and server_ip and server_port:
            try:
                server_port = int(server_port)
                server_entry = f"{server_name} ({server_ip}:{server_port})"
                self.server_listbox.insert(tk.END, server_entry)
                self.log_message(f"Added {server_entry}")
                if self.load_balancer:
                    self.load_balancer.backend_servers.append((server_ip, server_port))
                self.save_servers_to_json()
            except ValueError:
                self.log_message("Invalid port number. Please enter a valid integer.")
        
        self.update_topology()
        # Close the add server form
        self.add_server_window.destroy()

    def remove_server(self):
        # Remove selected server
        selected = self.server_listbox.curselection()
        if selected:
            server_entry = self.server_listbox.get(selected)
            self.server_listbox.delete(selected)
            self.log_message(f"Removed {server_entry}")
            if self.load_balancer:
                server_ip, server_port = server_entry.split(' (')[1].rstrip(')').split(':')
                self.load_balancer.backend_servers = [s for s in self.load_balancer.backend_servers if s[0] != server_ip or s[1] != int(server_port)]
            self.save_servers_to_json()
        self.update_topology()

    def start_load_balancer(self):
        backend_servers = []
        for server_entry in self.server_listbox.get(0, tk.END):
            server_name, server_ip_port = server_entry.split(' (')
            server_ip, server_port = server_ip_port.rstrip(')').split(':')
            backend_servers.append((server_ip, int(server_port)))
        
        self.load_balancer = LoadBalancer(port=7000, backend_servers=backend_servers, status_update_callback=self.log_message,algorithm=self.algorithm_combobox.current())
        self.load_balancer_thread = threading.Thread(target=self.load_balancer.start_load_balancer, daemon=True)
        self.load_balancer_thread.start()
        self.status_label.config(text="Status: Running")

    def stop_load_balancer(self):
        print("stop loadbalancer")
        if self.load_balancer:
            self.load_balancer.stop()
        if self.load_balancer_thread:
            self.load_balancer_thread.join(timeout=5)  # Timeout to prevent indefinite blocking
            self.load_balancer_thread = None  # Reset thread reference after joining
        self.status_label.config(text="Status: Stopped")
        self.log_message("Load Balancer Stopped")

    def update_topology(self):
        self.canvas.delete("all")

        # Get canvas size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Center coordinates
        center_x = canvas_width / 2
        center_y = canvas_height / 2

        # Draw Load Balancer (top center)
        lb_width, lb_height = 120, 50
        lb_x, lb_y = center_x, center_y - canvas_height / 3 
        self.canvas.create_rectangle(lb_x - lb_width // 2, lb_y - lb_height // 2, lb_x + lb_width // 2, lb_y + lb_height // 2, fill="orange")
        self.canvas.create_text(lb_x, lb_y, text="Load Balancer", font=("Arial", 12, "bold"))

        # Draw Servers
        servers = self.server_listbox.get(0, tk.END)
        num_servers = len(servers)
        server_radius = 30
        spacing = 150  # Horizontal spacing between servers
        start_x = center_x - (num_servers - 1) * spacing / 2

        if num_servers > 0:
            for i, server in enumerate(servers):
                server_x = start_x + i * spacing
                server_y = center_y + 30

                # Draw server circle
                self.canvas.create_oval(server_x - server_radius, server_y - server_radius, server_x + server_radius, server_y + server_radius, fill="lightblue")

                # Draw server name inside the circle
                server_name = server.split(' (')[0]
                self.canvas.create_text(server_x, server_y, text=server_name, font=("Arial", 8, "bold"))

                # Draw server details below the circle
                server_details = server.split(' (')[1].rstrip(')')
                server_ip, server_port = server_details.split(':')
                ip_text = f"IP: {server_ip}"
                port_text = f"Port: {server_port}"
                health_text = "Health: Unknown"  # Placeholder for health status
                request_count_text = "Requests: 0"  # Placeholder for request count

                detail_y_start = server_y + server_radius + 10
                server_font_size=8
                server_font='Arial'
                self.canvas.create_text(server_x, detail_y_start, text=ip_text, font=(server_font, server_font_size))
                self.canvas.create_text(server_x, detail_y_start + 15, text=port_text, font=(server_font, server_font_size))
                self.canvas.create_text(server_x, detail_y_start + 30, text=health_text, font=(server_font, server_font_size))
                self.canvas.create_text(server_x, detail_y_start + 45, text=request_count_text, font=(server_font, server_font_size))

                # Draw connection line to the load balancer
                self.canvas.create_line(lb_x, lb_y + lb_height // 2, server_x, server_y - server_radius, fill="green", width=2)
    
    def log_message(self, message):
        self.logger.log_message(message=message)

if __name__ == "__main__":
    app = LoadBalancerUI()
    app.mainloop()

