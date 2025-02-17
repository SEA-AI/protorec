"""Flask application initialization."""

__version__ = "0.1.0"

from flask import Flask, Response
from flask_cors import CORS


def create_app():
    """Create and configure the Flask application.

    Returns
    -------
    Flask
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Enable CORS with specific options
    CORS(app, supports_credentials=True)

    # Add no-cache headers to all responses
    @app.after_request
    def add_header(response: Response) -> Response:
        """Add headers to prevent caching."""
        response.headers[
            "Cache-Control"
        ] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Register blueprints
    from protorec.routes import main

    app.register_blueprint(main)

    return app
