import http.server
import os
import threading
import sys
import subprocess
import signal

def run_health_server():
    """Starts a minimal HTTP server to satisfy Cloud Run's health check."""
    port = int(os.environ.get("PORT", 8080))
    
    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        
        def log_message(self, format, *args):
            # Suppress logs for health checks to keep output clean
            return

    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, HealthHandler)
    print(f"Health check server started on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python health_check_wrapper.py <command> [args...]")
        sys.exit(1)

    # Start health server in a separate daemon thread
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Extract the command to run
    cmd = sys.argv[1:]
    
    print(f"Executing command: {' '.join(cmd)}")
    
    # Run the main process
    # We use Popen and wait to allow the health server to keep running in its thread
    process = subprocess.Popen(cmd)

    def signal_handler(sig, frame):
        print(f"Received signal {sig}, terminating child process...")
        process.terminate()
        sys.exit(0)

    # Forward termination signals to the child process
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    exit_code = process.wait()
    sys.exit(exit_code)
