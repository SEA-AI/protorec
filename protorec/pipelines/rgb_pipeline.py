"""RGB camera pipeline implementation for video recording.

This module provides the RGBPipeline class that implements a GStreamer pipeline
for recording from RGB/color cameras with NVIDIA hardware acceleration.
"""

from typing import Any, Dict, Optional

import numpy as np

from protorec.pipelines import Gst
from protorec.pipelines.pipeline import CameraPipeline


class RGBPipeline(CameraPipeline):
    """Pipeline implementation for RGB/color cameras.

    This class implements a GStreamer pipeline for recording from color cameras,
    with support for both recording to file and real-time frame access through
    an appsink element.
    """

    def __init__(self, config: Dict[str, Any], framerate: int = 30) -> None:
        """Initialize the RGB pipeline.

        Parameters
        ----------
        config : Dict[str, Any]
            Camera configuration dictionary
        framerate : int, optional
            Video framerate, by default 30
        """
        super().__init__(config, framerate)
        self._frame: Optional[np.ndarray] = None
        self.tee: Optional[Gst.Element] = None
        self.queue_recording: Optional[Gst.Element] = None
        self.appsink: Optional[Gst.Element] = None

    def _create_recording_elements(self) -> Dict[str, Optional[Gst.Element]]:
        """Create recording branch elements based on the configured format."""
        elements: Dict[str, Optional[Gst.Element]] = {}

        if self.format == ".avi":
            elements["encoder"] = Gst.ElementFactory.make("nvjpegenc", "nvjpegenc")
            elements["muxer"] = Gst.ElementFactory.make("avimux", "avimux")
        elif self.format == ".mp4":
            elements["encoder"] = Gst.ElementFactory.make("nvv4l2h264enc", "h264enc")
            if elements["encoder"] is not None:
                elements["encoder"].set_property("insert-sps-pps-at-idr", True)
                elements["encoder"].set_property("idrinterval", 30)
                elements["encoder"].set_property("EnableLossless", True)
                elements["encoder"].set_property("profile", 4)
            elements["parser"] = Gst.ElementFactory.make("h264parse", "h264parse")
            if elements["parser"] is not None:
                elements["parser"].set_property("config-interval", -1)
            elements["muxer"] = Gst.ElementFactory.make("qtmux", "qtmux")
        else:
            raise ValueError(
                f"Unsupported RGB recording format: {self.format}. "
                "Use '.avi' for MJPEG or '.mp4' for H.264 lossless."
            )

        return elements

    def _create_elements(self) -> Dict[str, Optional[Gst.Element]]:
        """Create all GStreamer elements for the pipeline."""
        elements: Dict[str, Optional[Gst.Element]] = {}

        # Common elements
        elements["videorate"] = Gst.ElementFactory.make("videorate", "videorate")
        elements["capsfilter"] = Gst.ElementFactory.make("capsfilter", "capsfilter")
        caps = Gst.Caps.from_string(
            f"video/x-raw(memory:NVMM),framerate={self.framerate}/1"
        )
        if elements["capsfilter"] is not None:
            elements["capsfilter"].set_property("caps", caps)

        elements["videoconvert"] = Gst.ElementFactory.make("nvvidconv", "nvvidconv")
        elements.update(self._create_recording_elements())

        # Appsink elements
        elements.update(self._create_appsink_elements())
        return elements

    def _create_appsink_elements(self) -> Dict[str, Optional[Gst.Element]]:
        """Create elements specific to the appsink branch."""
        elements: Dict[str, Optional[Gst.Element]] = {}
        elements["queue_appsink"] = Gst.ElementFactory.make("queue", "queue_appsink")
        if elements["queue_appsink"] is not None:
            elements["queue_appsink"].set_property("max-size-buffers", 5)
            elements["queue_appsink"].set_property("leaky", 2)

        elements["nvidconv_appsink"] = Gst.ElementFactory.make(
            "nvvidconv", "nvvidconv_appsink"
        )
        elements["videoconvert_appsink"] = Gst.ElementFactory.make(
            "videoconvert", "videoconvert_appsink"
        )
        elements["videorate_appsink"] = Gst.ElementFactory.make(
            "videorate", "videorate_appsink"
        )
        elements["capsfilter_appsink"] = Gst.ElementFactory.make(
            "capsfilter", "capsfilter_appsink"
        )

        caps_appsink = Gst.Caps.from_string("video/x-raw,format=BGR")
        if elements["capsfilter_appsink"] is not None:
            elements["capsfilter_appsink"].set_property("caps", caps_appsink)
        return elements

    def construct_pipeline(self) -> Gst.Pipeline:
        """Construct the GStreamer pipeline."""
        pipeline = Gst.Pipeline.new("pipeline" + self.config["name"])
        self.src = self.get_src()
        self.sink = self.get_sink()

        # Create elements
        elements = self._create_elements()

        # Create tee elements
        self.tee = Gst.ElementFactory.make("tee", "tee")
        self.queue_recording = Gst.ElementFactory.make("queue", "queue_recording")
        if self.queue_recording is not None:
            self.queue_recording.set_property("max-size-buffers", 5)
            self.queue_recording.set_property("leaky", 2)

        self.appsink = Gst.ElementFactory.make("appsink", "appsink")
        if self.appsink is not None:
            self.appsink.set_property("emit-signals", True)
            self.appsink.set_property("sync", True)
            self.appsink.set_property("max-buffers", 1)
            self.appsink.set_property("drop", True)

        # Check and add elements
        failed_elements = [
            name for name, element in elements.items() if element is None
        ]
        if failed_elements:
            raise RuntimeError(
                f"Failed to create elements: {', '.join(failed_elements)}"
            )

        for element in [
            self.src,
            *elements.values(),
            self.tee,
            self.queue_recording,
            self.sink,
            self.appsink,
        ]:
            if element is not None:
                pipeline.add(element)

        # Link elements
        self._link_pipeline_elements(elements)
        return pipeline

    def _link_pipeline_elements(
        self, elements: Dict[str, Optional[Gst.Element]]
    ) -> None:
        """Link all pipeline elements together."""
        # Link main elements
        if all(
            x is not None
            for x in [
                self.src,
                elements["videorate"],
                elements["capsfilter"],
                elements["videoconvert"],
                self.tee,
            ]
        ):
            self.src.link(elements["videorate"])
            elements["videorate"].link(elements["capsfilter"])
            elements["capsfilter"].link(elements["videoconvert"])
            elements["videoconvert"].link(self.tee)

        # Link recording branch
        recording_chain = [
            self.tee,
            self.queue_recording,
            elements["encoder"],
            elements.get("parser"),
            elements["muxer"],
            self.sink,
        ]
        if all(x is not None for x in recording_chain):
            self.tee.link(self.queue_recording)
            self.queue_recording.link(elements["encoder"])
            previous = elements["encoder"]
            if elements.get("parser") is not None:
                previous.link(elements["parser"])
                previous = elements["parser"]
            previous.link(elements["muxer"])
            elements["muxer"].link(self.sink)

        # Link appsink branch
        if all(
            x is not None
            for x in [
                elements["queue_appsink"],
                elements["nvidconv_appsink"],
                elements["videoconvert_appsink"],
                elements["capsfilter_appsink"],
                self.appsink,
            ]
        ):
            self.tee.link(elements["queue_appsink"])
            elements["queue_appsink"].link(elements["nvidconv_appsink"])
            elements["nvidconv_appsink"].link(elements["videoconvert_appsink"])
            elements["videoconvert_appsink"].link(elements["capsfilter_appsink"])
            elements["capsfilter_appsink"].link(self.appsink)
            self.appsink.connect("new-sample", self.callback)
