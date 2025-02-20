from gi.repository import Gst
from protorec import create_app
import sys
import os

Gst.init(sys.argv)

def run():

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--recdir", type=str, default="/home/lite/POWER_Data/SDCard/DataSink/prototype_recordings")
    parser.add_argument("--config", type=str, default="protorec/configs/cameras_config.json")
    args = parser.parse_args()

    if not os.path.exists(args.recdir):
        os.makedirs(args.recdir)

    app = create_app(args.config, args.recdir)
    app.run(host='0.0.0.0', port=5000)