import os
import sys
from pathlib import Path

import gi
from gi.repository import Gst

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")

from waitress import serve

from protorec import create_app

Gst.init(sys.argv)


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recdir",
        type=str,
        default=(
            Path.home() / "POWER_Data" / "SDCard" / "DataSink" / "prototype_recordings"
        ).as_posix(),
    )
    parser.add_argument(
        "--config",
        type=str,
        default=(Path.home() / "cameras_config.json").as_posix(),
    )
    args = parser.parse_args()

    if not os.path.exists(args.recdir):
        os.makedirs(args.recdir)

    app = create_app(args.config, args.recdir)
    serve(app, host="0.0.0.0", port=5000)
