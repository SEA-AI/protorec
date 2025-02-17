"""Command-line interface for the GST Recording application.

This module provides command-line interfaces for running the application in both
production and development modes. It includes a custom Gunicorn application class
for production deployment and a development server with debug capabilities.
"""

import argparse
from pathlib import Path
from typing import Any, Dict, Optional

import gunicorn.app.base
from flask import Flask


class GunicornApplication(gunicorn.app.base.Application):
    """Custom Gunicorn application for production deployment.

    This class extends Gunicorn's BaseApplication to provide a customized WSGI
    server implementation with configuration loading from a file.

    Parameters
    ----------
    app: The WSGI application to serve
    options: Optional dictionary of Gunicorn configuration options
    """

    def __init__(self, app: Flask, options: Optional[Dict[str, Any]] = None) -> None:
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self) -> None:
        """Load Gunicorn configuration from file and CLI options.

        Loads the default configuration from gunicorn_conf.py and then
        overrides settings with any provided CLI options.
        """
        # Load the default config file
        config_path = Path(__file__).parent / "gunicorn_conf.py"
        self.load_config_from_file(str(config_path))

        # Override with CLI options
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self) -> Flask:
        """Return the WSGI application to be run.

        Returns
        -------
        The Flask application instance
        """
        return self.application


def run_prod() -> None:
    """Run the production server using Gunicorn.

    Parses command line arguments and starts a production Gunicorn server
    with the specified configuration. Supports customization of host, port,
    number of workers, and log level.
    """
    parser = argparse.ArgumentParser(description="GST Recording App Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workers", type=int, help="Number of worker processes")
    parser.add_argument("--log-level", default="info", help="Logging level")

    args = parser.parse_args()

    # Import app here to avoid circular imports
    from protorec.wsgi import app

    options = {
        "bind": f"{args.host}:{args.port}",
        "workers": args.workers,
        "loglevel": args.log_level,
    }

    GunicornApplication(app, options).run()


def run_dev() -> None:
    """Run the development server with debug features.

    Parses command line arguments and starts a Flask development server
    with debug mode enabled. Supports customization of host, port, and
    auto-reload functionality.
    """
    parser = argparse.ArgumentParser(description="GST Recording App Development Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    # Import app here to avoid circular imports
    from protorec import create_app

    app = create_app()
    app.run(host=args.host, port=args.port, debug=True, use_reloader=args.reload)
