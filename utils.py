import requests
import sys
from datetime import datetime
import os


def get_session(base_url, auth):
    r = requests.get(f"{base_url}/lol-champ-select/v1/session", auth=auth, verify=False)
    return r.json() if r.status_code == 200 else None


# Simple logging system
class Logger:
    def __init__(self, log_file="league_auto_picker.log"):
        self.log_file = log_file
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        self.log_file = os.path.join("logs", log_file)

        # Redirect stdout and stderr to file
        self.log_handle = open(self.log_file, "a", encoding="utf-8")

    def start_logging(self):
        """Start redirecting prints to file"""
        sys.stdout = self
        sys.stderr = self

    def stop_logging(self):
        """Stop redirecting and restore original stdout/stderr"""
        if hasattr(self, "log_handle"):
            self.log_handle.close()
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

    def write(self, text):
        """Write to both file and original stdout"""
        # Only add timestamp if text is not empty and not just whitespace
        if text.strip():
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_text = f"[{timestamp}] {text}"

            # Write to file with timestamp
            self.log_handle.write(formatted_text)
            self.log_handle.flush()
        else:
            # For empty lines, just write to file without timestamp
            self.log_handle.write(text)
            self.log_handle.flush()

        # Always write to original stdout for console output (without timestamp)
        self.original_stdout.write(text)
        self.original_stdout.flush()

    def flush(self):
        """Flush both file and stdout"""
        self.log_handle.flush()
        self.original_stdout.flush()


# Global logger instance
logger = Logger()


def log_print(*args, **kwargs):
    """Custom print function that ensures logging"""
    print(*args, **kwargs)
