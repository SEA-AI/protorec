"""Base camera pipeline class for video recording.

This module provides the base CameraPipeline class that handles GStreamer pipeline
setup and control for video recording from different camera types.
"""

import os
from typing import Any, Dict, Optional

try:
    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    from gi.repository import Gst
except ImportError as e:
    raise ImportError(
        "GStreamer Python bindings not found. Please install gstreamer1.0-python3"
    ) from e


class CameraPipeline:
    """Base class for camera pipeline handling.

    This class provides the basic structure and methods for creating and
    controlling GStreamer pipelines for video recording.
    """

    def __init__(self, config: Dict[str, Any], framerate: int = 30) -> None:
        """Initialize the camera pipeline.

        Parameters
        ----------
        config : Dict[str, Any]
            Camera configuration dictionary containing:
            - name: Camera name
            - element: GStreamer source element
            - properties: Element properties
            - format: Output format
        framerate : int, optional
            Video framerate, by default 30
        """
        self.config = config
        self.framerate = framerate
        self.src: Optional[Gst.Element] = None
        self.sink: Optional[Gst.Element] = None
        self.pipeline: Gst.Pipeline = self.construct_pipeline()
        self.terminate = False
        self.dir = "."
        self.format = config["format"]

    def construct_pipeline(self) -> Gst.Pipeline:
        """Construct the GStreamer pipeline.

        This method should be implemented by subclasses to create
        their specific pipeline configurations.

        Returns
        -------
        Gst.Pipeline
            Configured GStreamer pipeline

        Raises
        ------
        NotImplementedError
            If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement construct_pipeline()")

    def get_src(self) -> Gst.Element:
        """Get source element and apply properties.

        Returns
        -------
        Gst.Element
            Configured source element
        """
        src = Gst.ElementFactory.make(self.config["element"], "src")
        if src is None:
            raise RuntimeError(f"Could not create {self.config['element']} element")

        for key, value in self.config["properties"].items():
            src.set_property(key, value)
        return src

    def get_sink(self) -> Gst.Element:
        """Get sink element.

        Returns
        -------
        Gst.Element
            Configured filesink element
        """
        sink = Gst.ElementFactory.make("filesink", "filesink")
        if sink is None:
            raise RuntimeError("Could not create filesink element")
        return sink

    def run(self) -> None:
        """Run the pipeline and set the sink location."""
        if self.sink is None:
            raise RuntimeError("Pipeline sink not initialized")

        self.sink.set_property(
            "location", os.path.join(self.dir, self.config["name"] + self.format)
        )
        self.pipeline.set_state(Gst.State.READY)
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self) -> None:
        """Stop the pipeline and set state to NULL."""
        self.pipeline.send_event(Gst.Event.new_eos())
        self.pipeline.set_state(Gst.State.NULL)

    def is_playing(self) -> bool:
        """Check if the pipeline is playing.

        Returns
        -------
        bool
            True if pipeline is in PLAYING state
        """
        _, state, _ = self.pipeline.get_state(timeout=Gst.CLOCK_TIME_NONE)
        return state == Gst.State.PLAYING

    def is_stopped(self) -> bool:
        """Check if the pipeline is stopped.

        Returns
        -------
        bool
            True if pipeline is in NULL state
        """
        _, state, _ = self.pipeline.get_state(timeout=Gst.CLOCK_TIME_NONE)
        return state == Gst.State.NULL

    def set_dir(self, dir_path: str) -> None:
        """Set the directory to save the video.

        Parameters
        ----------
        dir_path : str
            Path to directory where videos will be saved
        """
        self.dir = dir_path
