"""Routes for the application."""

from flask import Blueprint

main = Blueprint("main", __name__)


@main.route("/")
def hello():
    """Hello route."""
    return "Hello, World!"
