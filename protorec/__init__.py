__version__ = "0.1.0"

from flask import Flask, render_template, jsonify, Response
import time
import json
import os
from protorec.pipelines.rgb_pipeline import RGBPipeline
from protorec.pipelines.thermal_pipeline import ThermalPipeline
import cv2
import datetime
import numpy as np

def get_disk_usage(path="/"):
    stat = os.statvfs(path)
    
    total = (stat.f_blocks * stat.f_frsize) / (1024**3)  # Convert to GB
    free = (stat.f_bfree * stat.f_frsize) / (1024**3)    # Convert to GB
    used = total - free
    percent_used = (used / total) * 100

    return {"total": total, "free": free, "used": used}

class CameraManager:

    def __init__(self, config_path, recdir, streaming_camera="rgb"):
        self.is_recording = False
        self.recdir = recdir
        self.cameras_config = json.load(open(config_path, 'r'))
        self.camera_names = [self.cameras_config["cameras"][i]["name"] for i in range(len(self.cameras_config["cameras"]))]
        self.cameras = self._initialize_cameras()
        self.streaming_camera = self._validate_streaming_camera(self.cameras_config["streaming_camera"])
        self.recording_start_time = None  # Track when recording starts

    def _validate_streaming_camera(self, streaming_camera):
        if streaming_camera is None:
            return None
        elif streaming_camera not in self.camera_names:
            raise ValueError(f"Unknown camera name: {streaming_camera}, should be one of {self.camera_names}")
        elif self.cameras[streaming_camera].config["type"] != "color":
            raise ValueError(f"Camera {streaming_camera} is not a color camera, streaming is only supported for color cameras")
        else:
            return streaming_camera
            
    def _initialize_cameras(self):
        cameras = {}
        for camera_config in self.cameras_config["cameras"]:
            if camera_config["type"] == "color":
                cameras[camera_config["name"]] = RGBPipeline(camera_config)
            elif camera_config["type"] == "thermal":
                cameras[camera_config["name"]] = ThermalPipeline(camera_config)
            else:
                raise ValueError(f"Unknown camera type: {camera_config['type']}, should be either 'color' or 'thermal'")
        return cameras

    def start_recording(self):
        if self.is_recording:
            return {"status": "already recording"}

        self.is_recording = True
        self.recording_start_time = datetime.datetime.now()  # Store start time
        folder = time.strftime('%Y-%m-%d-%H-%M-%S')
        directory = os.path.join(self.recdir, folder)
        os.makedirs(directory, exist_ok=True)

        for camera_pipeline in self.cameras.values():
            camera_pipeline.set_dir(directory)

        for camera_pipeline in self.cameras.values():
            camera_pipeline.run()

        while not all(camera_pipeline.is_playing() for camera_pipeline in self.cameras.values()):
            pass

        return {"status": "recording started"}

    def stop_recording(self):
        if not self.is_recording:
            return {"status": "already stopped"}

        for camera_pipeline in self.cameras.values():
            camera_pipeline.stop()

        while not all(camera_pipeline.is_stopped() for camera_pipeline in self.cameras.values()):
            pass

        self.is_recording = False
        self.recording_start_time = None  # Reset start time
        return {"status": "recording stopped"}

    def get_state(self):
        elapsed_time = None
        if self.is_recording and self.recording_start_time:
            elapsed_time = (datetime.datetime.now() - self.recording_start_time).total_seconds()

        return {
            "is_recording": self.is_recording,
            "recording_duration": elapsed_time,
        }

    def get_frame(self):
        if self.streaming_camera is None:
            return np.zeros((720, 1280, 3), dtype=np.uint8)

        frame = self.cameras[self.streaming_camera].get_frame()
        if frame is None:
            return np.zeros((720, 1280, 3), dtype=np.uint8) #empty frame
        
        frame = cv2.resize(frame, (1280, 720))

        return frame

def create_app(config_path, recdir):
    app = Flask(__name__)
    camera_manager = CameraManager(config_path, recdir)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/get_state', methods=['GET'])
    def get_state():
        state = camera_manager.get_state()
        disk_usage = get_disk_usage(recdir)  # Get disk usage details
        state.update({"disk_usage": disk_usage})  # Add disk usage to the response
        return jsonify(state)


    @app.route('/start_recording', methods=['POST'])
    def start_recording():
        return jsonify(camera_manager.start_recording())

    @app.route('/stop_recording', methods=['POST'])
    def stop_recording():
        return jsonify(camera_manager.stop_recording())

    @app.route('/frame')
    def get_frame():
        frame = camera_manager.get_frame()
        _, buffer = cv2.imencode('.jpg', frame)
        return Response(buffer.tobytes(), mimetype='image/jpeg')

    return app