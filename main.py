import time
import tkinter as tk
from tkinter import ttk
import json
import threading
from loadbalancer import LoadBalancer
import datetime
from logger import Logger
import os
import sys
from tkinter import font
from utils import clear_port

class LoadBalancerUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HTTP Load Balancer")
        self.geometry("600x400")

        self.is_lb_running = False

        #configurations directories set to current working directory
        self.serverfile_directory = os.getcwd()
        self.logfile_directory = os.getcwd()
        self.configfile_directory = os.getcwd()
        self.health_check_circle = 5 #set default to 5 
        self.maximum_servers = 5 
        self.load_config_from_json()
        # Server List Section
        self.server_frame = ttk.LabelFrame(self, text="Server List")
        self.server_frame.pack(fill="both", padx=10, pady=10, expand=True)
        server_font = font.Font(family="Helvetica", size=16)
        # Server Listbox
        self.server_listbox = tk.Listbox(self.server_frame, height=5)
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

        add_btn_style = ttk.Style()
        add_btn_style.configure("Add.TButton", background="#6aa84f", foreground="#ffffff")
        remove_btn_style = ttk.Style()
        remove_btn_style.configure("Remove.TButton", background="#cc0000", foreground="#ffffff")
        self.add_server_button = ttk.Button(button_frame, text="Add Server", command=self.show_add_server_form,style="Add.TButton")
        self.add_server_button.pack(side="left", padx=5)

        self.remove_server_button = ttk.Button(button_frame, text="Remove Server", command=self.remove_server,style="Remove.TButton")
        self.remove_server_button.pack(side="left", padx=5)

        # Load Balancer Control Section
        self.control_frame = ttk.LabelFrame(self, text="Load Balancer Control")
        self.control_frame.pack(fill="x", padx=10, pady=10)
        # Algorithm Selection
        ttk.Label(self.control_frame, text="Select Algorithm:").pack(side="left", padx=10)
        self.algorithm_var = tk.StringVar()
        self.algorithm_list = ["Round Robin", "Least Connections", "IP Hash"]
        self.algorithm_combobox = ttk.Combobox(
            self.control_frame, 
            textvariable=self.algorithm_var, 
            values = self.algorithm_list
        )
        self.algorithm_combobox.current(0)  # Set default to "Round Robin"
        self.algorithm_combobox.pack(side="left", padx=10, pady=5)

        stop_btn_style = ttk.Style()
        stop_btn_style.configure("Stop.TButton", background="#800020", foreground="#ffffff")
        start_btn_style = ttk.Style()
        start_btn_style.configure("Start.TButton", background="#38761d", foreground="#ffffff")
        

        # Start/Stop Buttons
        self.start_button = ttk.Button(self.control_frame, text="Start Load Balancer", command=self.start_load_balancer,style='Start.TButton')
        self.start_button.pack(side="left", padx=10, pady=5)

        self.stop_button = ttk.Button(self.control_frame, text="Stop Load Balancer", command=self.stop_load_balancer,state=tk.DISABLED,style='Stop.TButton')
        self.stop_button.pack(side="left", padx=10, pady=5)

        # Status Label
        self.status_label = ttk.Label(self.control_frame, text="Status: Stopped")
        self.status_label.pack(side="left", padx=20, pady=5)

        # Add Config button
        self.config_button = tk.Button(self.control_frame, text="Config", command=self.open_config_popup,background="#cfe2f3")
        self.config_button.pack(side=tk.LEFT)

        # Logs/Status Sectionbackground
        self.log_frame = ttk.LabelFrame(self, text="Logs")
        self.log_frame.pack(fill="both", padx=10, pady=10, expand=True)

        self.log_text = tk.Text(self.log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", padx=10, pady=10, expand=True)
        
        
        self.load_balancer = None
        self.load_balancer_thread = None
        self.logger = Logger(self.log_text,self.logfile_directory)

        self.load_servers_from_json()


        # Bind the canvas resize event to update topology
        self.canvas.bind("<Configure>", lambda event: self.update_topology())
    def restart_program(self):
        """Restart the current program."""
        print("Restarting program...")
        # python = sys.executable
        # os.execl(python, python, *sys.argv)
        self.stop_load_balancer()
        self.start_load_balancer()

    def save_servers_to_json_and_restart(self):
        servers = []
        for i in range(self.server_listbox.size()):
            server_entry = self.server_listbox.get(i)
            name, ip_port = server_entry.split(' (')
            ip, port = ip_port.rstrip(')').split(':')
            servers.append({"name": name, "ip": ip, "port": int(port)})
        serversFile = 'servers.json'
        serversFile = os.path.join(self.serverfile_directory,serversFile)
        print(serversFile , " Server file location")
        with open(serversFile, 'w') as f:
            json.dump(servers, f, indent=4)
        # time.sleep(3)
        
    def load_servers_from_json(self):
        serversFile = "servers.json"
        serversFile = os.path.join(self.serverfile_directory,serversFile)
        try:
            with open(serversFile, 'r') as f:
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
        servers = len(self.server_listbox.get(0, tk.END))
        print(self.maximum_servers , ' Max ')
        if(servers >= self.maximum_servers):
            self.log_message(f"Denied adding more server! Max servers is : {self.maximum_servers}")
            self.add_server_window.destroy()#close the pop up
            return
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
                self.save_servers_to_json_and_restart()
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
            self.update_topology()
            self.save_servers_to_json_and_restart()
        

    def is_load_balancer_running(self):
        return isinstance(self.load_balancer_thread,threading.Thread) and self.load_balancer_thread.is_alive()
    
    def start_load_balancer(self):
        if(not self.is_load_balancer_running()):
            print('New Thread Starts...')
            clear_port(self.lb_port)# clear the port's process
            backend_servers = []
            for server_entry in self.server_listbox.get(0, tk.END):
                server_name, server_ip_port = server_entry.split(' (')
                server_ip, server_port = server_ip_port.rstrip(')').split(':')
                backend_servers.append((server_ip, int(server_port)))
            selected_algorithm = self.algorithm_combobox.current()
            if selected_algorithm not in self.algorithm_list:
                selected_algorithm = 'round_robin'
            self.load_balancer = LoadBalancer(port=self.lb_port, backend_servers=backend_servers, status_update_callback=self.log_message,update_topology_callback=self.update_topology,algorithm=selected_algorithm,health_check_circle=self.health_check_circle)
            self.load_balancer_thread = threading.Thread(target=self.load_balancer.start_load_balancer, daemon=True)
            self.load_balancer_thread.start()
            self.status_label.config(text="Status: Running")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.add_server_button.config(state=tk.DISABLED)
            self.remove_server_button.config(state=tk.DISABLED)
            self.config_button.config(state=tk.DISABLED)


    def stop_load_balancer(self):
        print("stop loadbalancer")
        if isinstance(self.load_balancer,LoadBalancer) and isinstance(self.load_balancer_thread,threading.Thread):
            self.load_balancer.stop()
            self.load_balancer_thread.join(5)  # Timeout to prevent indefinite blocking
            self.load_balancer_thread = None  # Reset thread reference after joining
            self.load_balancer = None #reset load_balancer reference
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Stopped")
            self.log_message("Load Balancer Stopped")
            self.add_server_button.config(state=tk.NORMAL)
            self.remove_server_button.config(state=tk.NORMAL)
            self.config_button.config(state=tk.NORMAL)
        self.update_topology()
    def update_topology(self):
        # Get canvas size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Center coordinates
        center_x = canvas_width / 2
        center_y = canvas_height / 2

        # Load Balancer dimensions and positioning
        lb_width, lb_height = 120, 50
        lb_x, lb_y = center_x, center_y - canvas_height / 3  # Top center position for load balancer
        lb_tag = "load_balancer"

        # Clear the canvas before drawing (useful for dynamic updates)
        self.canvas.delete("all")

        # Draw Load Balancer
        self.canvas.create_rectangle(
            lb_x - lb_width // 2, lb_y - lb_height // 2,
            lb_x + lb_width // 2, lb_y + lb_height // 2,
            fill="orange", tags=lb_tag
        )
        self.canvas.create_text(
            lb_x, lb_y, text=f"Load Balancer\n{'        '} {self.lb_port}",
            font=("Arial", 12, "bold"), tags=lb_tag
        )

        # Draw or update Servers
        servers = self.server_listbox.get(0, tk.END)
        num_servers = len(servers)
        server_radius = 30
        spacing = 150  # Horizontal spacing between servers

        # Calculate total width required for all servers
        total_width = (num_servers - 1) * spacing
        start_x = center_x - total_width / 2  # Adjust starting position to center the servers

        servers_status = {}
        if self.load_balancer:
            servers_status = self.load_balancer.get_server_status()

        for i, server in enumerate(servers):
            server_details = server.split(' (')[1].rstrip(')')
            server_ip, server_port = server_details.split(':')
            ip_port = (server_ip, int(server_port))
            status = servers_status.get(ip_port, {'health': 'Unknown', 'requests': 0})
            health = status['health']
            server_color = 'red' if health == "Unhealthy" else 'green'

            # Calculate server position
            server_x = start_x + i * spacing
            server_y = center_y + 30  # Placed below load balancer

            server_tag = f"server_{server_ip}_{server_port}"

            # Draw server circle
            self.canvas.create_oval(
                server_x - server_radius, server_y - server_radius,
                server_x + server_radius, server_y + server_radius,
                fill=server_color, tags=("server", server_tag)
            )

            # Draw server name inside the circle
            server_name = server.split(' (')[0]
            self.canvas.create_text(
                server_x, server_y, text=server_name,
                font=("Arial", 8, "bold"), tags=(server_tag,)
            )

            # Draw additional server details below the circle
            detail_y_start = server_y + server_radius + 10
            self.canvas.create_text(
                server_x, detail_y_start, text=f"IP: {server_ip}",
                font=("Arial", 8), tags=(server_tag,)
            )
            self.canvas.create_text(
                server_x, detail_y_start + 15, text=f"Port: {server_port}",
                font=("Arial", 8), tags=(server_tag,)
            )
            self.canvas.create_text(
                server_x, detail_y_start + 30, text=f"Health: {health}",
                font=("Arial", 8), tags=(server_tag,)
            )
            self.canvas.create_text(
                server_x, detail_y_start + 45, text=f"Requests: {status['requests']}",
                font=("Arial", 8), tags=(server_tag,)
            )

            # Draw connection line to the load balancer
            line_color = 'green' if health != "Unhealthy" else 'red'
            self.canvas.create_line(
                lb_x, lb_y + lb_height // 2, server_x, server_y - server_radius,
                fill=line_color, width=2, tags=(server_tag,)
            )

    def open_config_popup(self):
        self.config_button.config(state=tk.DISABLED)
        # Create a new top-level window for JSON input
        self.popup = tk.Toplevel(self)
        self.popup.title("Configure Load Balancer")

        label = tk.Label(self.popup, text="Enter JSON Configuration:")
        label.pack(padx=10, pady=10)

        self.config_json = tk.Text(self.popup, width=50, height=30)
        self.config_json.pack(padx=10, pady=10)

        # Set default JSON template
        default_json = {
            "serverfile_directory": self.serverfile_directory,
            "logfile_directory": self.logfile_directory,
            "configfile_directory":self.configfile_directory,
            "maximum_servers": self.maximum_servers,
            "health_check_circle": self.health_check_circle,
            "lb_port":self.lb_port
        }
        self.config_json.insert(tk.END, json.dumps(default_json, indent=4))

        apply_button = tk.Button(self.popup, text="Apply", command=self.save_config)
        apply_button.pack(side=tk.LEFT, padx=5, pady=10)

        cancel_button = tk.Button(self.popup, text="Cancel", command=self.cancel_config_edit)
        cancel_button.pack(side=tk.RIGHT, padx=5, pady=10)

    def cancel_config_edit(self):
        self.config_button.config(state=tk.NORMAL)
        self.popup.destroy()
    def save_config(self):
        try:
            config = json.loads(self.config_json.get("1.0", tk.END).strip())
           
            # Access values and adds them to self.attributes
            self.serverfile_directory = config.get('serverfile_directory')
            self.logfile_directory = config.get('logfile_directory')
            self.configfile_directory = config.get('configfile_directory')
            self.maximum_servers = config.get('maximum_servers')
            self.health_check_circle = config.get('health_check_circle')
            self.lb_port = config.get('lb_port')
            self.save_config_to_json()
            self.popup.destroy()
            self.config_button.config(state=tk.NORMAL)
        except json.JSONDecodeError:
            self.show_error_popup("Invalid JSON", "The provided JSON is invalid. Please correct it and try again.")
    
    def show_error_popup(self, title, message):
        error_popup = tk.Toplevel(self)
        error_popup.title(title)

        error_label = tk.Label(error_popup, text=message, fg='red')
        error_label.pack(padx=10, pady=10)

        close_button = tk.Button(error_popup, text="Close", command=error_popup.destroy)
        close_button.pack(pady=10)

    def load_config_from_json(self):
        # Path to your JSON file
        config_path = os.path.join(self.configfile_directory,'config.json')

        # Open and read the JSON file
        with open(config_path, 'r') as file:
            config_data = json.load(file)

        # Access values from the JSON data
        self.serverfile_directory = config_data.get('serverfile_directory')
        self.logfile_directory = config_data.get('logfile_directory')
        self.configfile_directory = config_data.get('configfile_directory')
        self.maximum_servers = config_data.get('maximum_servers')
        self.health_check_circle = config_data.get('health_check_circle')
        self.lb_port = config_data.get('lb_port')
    def save_config_to_json(self):
            # Create a dictionary with the configuration data
            config_data = {
                "serverfile_directory": self.serverfile_directory,
                "logfile_directory": self.logfile_directory,
                "configfile_directory": self.configfile_directory,
                "health_check_circle": self.health_check_circle,
                "maximum_servers": self.maximum_servers,
                "lb_port":self.lb_port
            }

            # Create the path for config
            config_path = os.path.join(self.configfile_directory, 'config.json')

            # Write the configuration data to a JSON file
            with open(config_path, 'w') as file:
                json.dump(config_data, file, indent=4)

            self.log_message(f"Configuration saved to {config_path}")

    def log_message(self, message):
        self.logger.log_message(message=message)
        self.log_text.see(tk.END)

if __name__ == "__main__":
    app = LoadBalancerUI()
    app.mainloop()

