"""Gunicorn configuration for GST Recording application.

This configuration is optimized for an application that:
1. Handles hardware interactions (sensors, recording devices)
2. Manages stateful operations (active recordings)
3. Requires consistent client-server connections
"""

# Server socket
bind = "0.0.0.0:8000"
backlog = 64  # Reduced backlog since we expect fewer concurrent connections

# Worker processes
workers = 1  # Single worker to prevent race conditions with hardware
worker_class = "sync"  # Synchronous workers for predictable hardware access
worker_connections = 100  # Reduced connections per worker
timeout = 120  # Increased timeout for long-running recording operations
keepalive = 5

# Graceful shutdown
graceful_timeout = 30
max_requests = 100  # Restart workers periodically to prevent memory leaks
max_requests_jitter = 10

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True  # Capture stdout/stderr from workers
enable_stdio_inheritance = True  # Ensure hardware communication is logged

# Process naming
proc_name = "gst-rec-app"

# Process management
preload_app = True  # Load application code before forking
reload = False  # Disable auto-reload in production
