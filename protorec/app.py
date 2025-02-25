"""Command line interface for the protorec application.

This module provides the entry point for running the protorec web server,
handling command line arguments and server configuration.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

try:
    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    from gi.repository import Gst
except ImportError:
    print(
        "Error: GStreamer Python bindings not found. Please install gstreamer1.0-python3"
    )
    sys.exit(1)

from waitress import serve

from protorec import create_app

# Initialize GStreamer
Gst.init(sys.argv)


def run() -> NoReturn:
    """Run the protorec web server.

    This function parses command line arguments, sets up the recording directory,
    initializes the Flask application, and starts the web server.

    Command line arguments:
        --recdir: Path to recording directory (default: ~/POWER_Data/SDCard/DataSink/prototype_recordings)
        --config: Path to camera configuration file (default: ~/cameras_config.json)
    """
    parser = argparse.ArgumentParser(description="Run the protorec web server")
    parser.add_argument(
        "--recdir",
        type=str,
        default=(
            Path.home() / "POWER_Data" / "SDCard" / "DataSink" / "prototype_recordings"
        ).as_posix(),
        help="Path to recording directory",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=(Path.home() / "cameras_config.json").as_posix(),
        help="Path to camera configuration file",
    )
    args = parser.parse_args()

    if not os.path.exists(args.recdir):
        os.makedirs(args.recdir)

    app = create_app(args.config, args.recdir)
    serve(app, host="0.0.0.0", port=5000)
