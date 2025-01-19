import os
from datetime import datetime
import tkinter as tk
class Logger:
    def __init__(self,log_text,logfile_directory):
        self.log_text = log_text #log_text is the object ref for log display in UI
        self.log_file = os.path.join(logfile_directory,"load_balancer_logs.txt")
        self.max_log_size = 5 * 1024 * 1024  # 5 MB

    # def log_message(self, message):
    #     # Rotate log file if needed 72.92

    #     self.rotate_log_file_if_needed()

    #     # Get the current time
    #     current_time = datetime.now()  # Correct usage
    #     formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    #     # Format the log message
    #     log_entry = f"{formatted_time} - {message}\n"

    #     # Update the log text widget
    #     self.log_text.config(state="normal")
    #     self.log_text.insert(tk.END, log_entry)
    #     self.log_text.config(state="disabled")

    #     # Write the log entry to a file
    #     with open(self.log_file, "a") as log_file:
    #         log_file.write(log_entry)
    def log_message(self, message, danger_alert=False):
        # Rotate log file if needed
        self.rotate_log_file_if_needed()

        # Get the current time
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

        # Format the log message
        log_entry = f"{formatted_time} - {message}\n"

        # Update the log text widget
        self.log_text.configure(state="normal")

        if danger_alert:
            self.log_text.tag_config("red_text", foreground="red")
            self.log_text.insert(tk.END, log_entry, "red_text")
        else:
            self.log_text.insert(tk.END, log_entry)

        self.log_text.configure(state="disabled")

        # Write the log entry to a file
        with open(self.log_file, "a") as log_file:
            log_file.write(log_entry)

    def rotate_log_file_if_needed(self):
        if os.path.exists(self.log_file) and os.path.getsize(self.log_file) >= self.max_log_size:
            base, ext = os.path.splitext(self.log_file)
            # Get the current time
            current_time = datetime.now()  # Correct usage
            formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
            rotated_log_file = f"{base}_{formatted_time}_{ext}"
            if os.path.exists(rotated_log_file):
                os.remove(rotated_log_file)
            os.rename(self.log_file, rotated_log_file)
