"""Main module for the protorec package providing camera recording functionality.

The module provides functionality for managing multiple camera pipelines,
recording video streams, and serving a web interface for control.
"""

from __future__ import annotations

import datetime
import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Union

import cv2  # type: ignore
import numpy as np
from flask import Flask, Response, jsonify, render_template, request

from protorec.pipelines import RGBPipeline, ThermalPipeline

__version__ = "0.2.0"

MAX_ZOOM = 8.0


def get_disk_usage(path: str = "/") -> Dict[str, float]:
    """Get disk usage statistics for the specified path.

    Parameters
    ----------
    path : str, optional
        Directory path to check disk usage for, by default "/"

    Returns
    -------
    Dict[str, float]
        Dictionary containing total, free and used disk space in GB with keys:
        - 'total': Total disk space in GB
        - 'free': Free disk space in GB
        - 'used': Used disk space in GB
        - 'percent_used': Percentage of disk space used
    """
    stat = os.statvfs(path)

    total = (stat.f_blocks * stat.f_frsize) / (1024**3)  # Convert to GB
    free = (stat.f_bfree * stat.f_frsize) / (1024**3)  # Convert to GB
    used = total - free
    percent_used = (used / total) * 100

    return {"total": total, "free": free, "used": used, "percent_used": percent_used}


def crop_zoom(frame: np.ndarray, zoom: float, cx: float, cy: float) -> np.ndarray:
    """Crop the frame to the region shown at the given zoom level.

    Parameters
    ----------
    frame : np.ndarray
        Full-resolution frame with shape (height, width, channels)
    zoom : float
        Zoom factor, clamped to [1, MAX_ZOOM]; 1 keeps the whole frame
    cx : float
        Horizontal crop center as a fraction of the frame width
    cy : float
        Vertical crop center as a fraction of the frame height

    Returns
    -------
    np.ndarray
        View of the cropped region, shifted to stay inside the frame
    """
    zoom = min(max(zoom, 1.0), MAX_ZOOM)
    height, width = frame.shape[:2]
    crop_width = max(1, round(width / zoom))
    crop_height = max(1, round(height / zoom))
    left = min(max(round(cx * width - crop_width / 2), 0), width - crop_width)
    top = min(max(round(cy * height - crop_height / 2), 0), height - crop_height)
    return frame[top : top + crop_height, left : left + crop_width]


def _float_arg(name: str, default: float) -> float:
    """Read a finite float query parameter from the current request.

    Parameters
    ----------
    name : str
        Query parameter name
    default : float
        Value used when the parameter is missing, invalid or not finite

    Returns
    -------
    float
        Parsed parameter value
    """
    value = request.args.get(name, default, type=float)
    return value if math.isfinite(value) else default


class CameraManager:
    """Manages multiple camera pipelines for recording and streaming.

    This class handles initialization of camera pipelines, recording control,
    and frame retrieval for streaming.
    """

    def __init__(self, config_path: str, recdir: str) -> None:
        """Initialize the camera manager.

        Parameters
        ----------
        config_path : str
            Path to camera configuration JSON file
        recdir : str
            Directory to store recordings
        """
        self.is_recording: bool = False
        self.recdir: str = recdir
        self.cameras_config: Dict[str, Any] = json.load(open(config_path, "r"))
        self.camera_names: List[str] = [
            self.cameras_config["cameras"][i]["name"]
            for i in range(len(self.cameras_config["cameras"]))
        ]
        self.cameras: Dict[str, Union[RGBPipeline, ThermalPipeline]] = (
            self._initialize_cameras()
        )
        self.streaming_camera: Optional[str] = self._validate_streaming_camera(
            self.cameras_config["streaming_camera"]
        )
        self.recording_start_time: Optional[datetime.datetime] = None
        self._start_preview()

    def _start_preview(self) -> None:
        """Start the preview of the streaming camera, if one is configured."""
        if self.streaming_camera is not None:
            self.cameras[self.streaming_camera].start_preview()

    def _stop_preview(self) -> None:
        """Stop the preview of the streaming camera, if one is configured."""
        if self.streaming_camera is not None:
            self.cameras[self.streaming_camera].stop_preview()

    def _validate_streaming_camera(
        self, streaming_camera: Optional[str]
    ) -> Optional[str]:
        """Validate the streaming camera configuration.

        Parameters
        ----------
        streaming_camera : Optional[str]
            Name of camera to validate

        Returns
        -------
        Optional[str]
            Validated streaming camera name or None

        Raises
        ------
        ValueError
            If camera name is invalid or not a color camera
        """
        if streaming_camera is None:
            return None
        elif streaming_camera not in self.camera_names:
            raise ValueError(
                f"Unknown camera name: {streaming_camera}, should be one of {self.camera_names}"
            )
        elif self.cameras[streaming_camera].config["type"] not in ["color", "thermal"]:
            raise ValueError(
                f"Camera {streaming_camera} is not a color/thermal camera, streaming is only supported for color/thermal cameras"
            )
        else:
            return streaming_camera

    def _initialize_cameras(self) -> Dict[str, Union[RGBPipeline, ThermalPipeline]]:
        """Initialize camera pipeline objects based on configuration.

        Returns
        -------
        Dict[str, Union[RGBPipeline, ThermalPipeline]]
            Dictionary mapping camera names to pipeline objects

        Raises
        ------
        ValueError
            If unknown camera type specified in config
        """
        cameras = {}
        for camera_config in self.cameras_config["cameras"]:
            if camera_config["type"] == "color":
                cameras[camera_config["name"]] = RGBPipeline(camera_config)
            elif camera_config["type"] == "thermal":
                cameras[camera_config["name"]] = ThermalPipeline(camera_config)
            else:
                raise ValueError(
                    f"Unknown camera type: {camera_config['type']}, should be either 'color' or 'thermal'"
                )
        return cameras

    def start_recording(self) -> Dict[str, str]:
        """Start recording from all cameras.

        Returns
        -------
        Dict[str, str]
            Status dictionary indicating if recording started
        """
        if self.is_recording:
            return {"status": "already recording"}

        self.is_recording = True
        self.recording_start_time = datetime.datetime.now()
        folder = time.strftime("%Y-%m-%d-%H-%M-%S")
        directory = os.path.join(self.recdir, folder)
        os.makedirs(directory, exist_ok=True)

        for camera_pipeline in self.cameras.values():
            camera_pipeline.set_dir(directory)

        # The recording pipeline opens the same camera as the preview
        self._stop_preview()
        for camera_pipeline in self.cameras.values():
            camera_pipeline.run()

        while not all(
            camera_pipeline.is_playing() for camera_pipeline in self.cameras.values()
        ):
            pass

        return {"status": "recording started"}

    def stop_recording(self) -> Dict[str, str]:
        """Stop recording from all cameras.

        Returns
        -------
        Dict[str, str]
            Status dictionary indicating if recording stopped
        """
        if not self.is_recording:
            return {"status": "already stopped"}

        for camera_pipeline in self.cameras.values():
            camera_pipeline.stop()

        while not all(
            camera_pipeline.is_stopped() for camera_pipeline in self.cameras.values()
        ):
            pass

        self.is_recording = False
        self.recording_start_time = None
        self._start_preview()
        return {"status": "recording stopped"}

    def get_state(self) -> Dict[str, Any]:
        """Get current recording state.

        Returns
        -------
        Dict[str, Any]
            Dictionary with recording status and elapsed time containing:
            - 'is_recording': bool indicating if recording is active
            - 'recording_duration': float of elapsed seconds if recording, else None
        """
        elapsed_time = None
        if self.is_recording and self.recording_start_time:
            elapsed_time = (
                datetime.datetime.now() - self.recording_start_time
            ).total_seconds()

        return {
            "is_recording": self.is_recording,
            "recording_duration": elapsed_time,
        }

    def get_frame(
        self, zoom: float = 1.0, cx: float = 0.5, cy: float = 0.5
    ) -> np.ndarray:
        """Get current frame from streaming camera.

        Parameters
        ----------
        zoom : float, optional
            Zoom factor applied to the full-resolution frame, by default 1.0
        cx : float, optional
            Horizontal zoom center as a fraction of the frame width, by default 0.5
        cy : float, optional
            Vertical zoom center as a fraction of the frame height, by default 0.5

        Returns
        -------
        np.ndarray
            Current video frame as numpy array with shape (720, 1280, 3)
        """
        if self.streaming_camera is None:
            return np.zeros((720, 1280, 3), dtype=np.uint8)

        frame = self.cameras[self.streaming_camera].get_frame()
        if frame is None:
            return np.zeros((720, 1280, 3), dtype=np.uint8)

        frame = cv2.resize(crop_zoom(frame, zoom, cx, cy), (1280, 720))
        return frame


def create_app(config_path: str, recdir: str) -> Flask:
    """Create and configure the Flask application.

    Parameters
    ----------
    config_path : str
        Path to camera configuration file
    recdir : str
        Directory to store recordings

    Returns
    -------
    Flask
        Configured Flask application instance
    """
    app = Flask(__name__)
    camera_manager = CameraManager(config_path, recdir)

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    @app.route("/get_state", methods=["GET"])
    def get_state() -> Response:
        state = camera_manager.get_state()
        disk_usage = get_disk_usage(recdir)
        state.update({"disk_usage": disk_usage})
        return jsonify(state)

    @app.route("/start_recording", methods=["POST"])
    def start_recording() -> Response:
        return jsonify(camera_manager.start_recording())

    @app.route("/stop_recording", methods=["POST"])
    def stop_recording() -> Response:
        return jsonify(camera_manager.stop_recording())

    @app.route("/frame")
    def get_frame() -> Response:
        frame = camera_manager.get_frame(
            zoom=_float_arg("zoom", 1.0),
            cx=_float_arg("cx", 0.5),
            cy=_float_arg("cy", 0.5),
        )
        _, buffer = cv2.imencode(".jpg", frame)
        return Response(buffer.tobytes(), mimetype="image/jpeg")

    return app
