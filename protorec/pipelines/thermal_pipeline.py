"""Thermal camera pipeline implementation for video recording.

This module provides the ThermalPipeline class that implements a GStreamer pipeline
for recording from thermal cameras with 16-bit grayscale output.
"""

from typing import Any, Dict, Optional

import numpy as np

from protorec.pipelines import Gst
from protorec.pipelines.pipeline import CameraPipeline


class ThermalPipeline(CameraPipeline):
    """Pipeline implementation for thermal cameras.

    This class implements a GStreamer pipeline for recording from thermal cameras,
    handling 16-bit grayscale format conversion and recording.
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

    def _create_elements(self) -> Dict[str, Optional[Gst.Element]]:
        """Create all GStreamer elements for the pipeline."""
        elements: Dict[str, Optional[Gst.Element]] = {}

        # Common elements
        elements["videorate"] = Gst.ElementFactory.make("videorate", "videorate")
        elements["capsfilter_16_le"] = Gst.ElementFactory.make("capsfilter", "capsfilter16_le")
        caps_16_le = Gst.Caps.from_string(f"video/x-raw,framerate={self.framerate}/1,format=GRAY16_LE")
        elements["capsfilter_16_le"].set_property("caps", caps_16_le)

        # Recording elements
        elements["videoconvert_recording"] = Gst.ElementFactory.make("videoconvert", "videoconvert_recording")
        elements["capsfilter16_be"] = Gst.ElementFactory.make("capsfilter", "capsfilter16_be")
        caps_16_be = Gst.Caps.from_string(f"video/x-raw,framerate={self.framerate}/1,format=GRAY16_BE")
        elements["capsfilter16_be"].set_property("caps", caps_16_be)

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

        elements["videoconvert_visualisation"] = Gst.ElementFactory.make("videoconvert", "videoconvert_visualisation")

        elements["visualisation"] = Gst.ElementFactory.make("visualisation", "visualisation")
        elements["visualisation"].set_property("display_mode", "clahe")
        elements["visualisation"].set_property("display-linear-cutoff-frequency", 0.5)
        elements["visualisation"].set_property("display-lower-saturation-thr", 15000)
        elements["visualisation"].set_property("display-upper-saturation-thr", 28000)

        elements["videoconvert_appsink"] = Gst.ElementFactory.make("videoconvert", "videoconvert_appsink")

        elements["capsfilter_appsink"] = Gst.ElementFactory.make("capsfilter", "capsfilter_appsink")
        caps_visualisation = Gst.Caps.from_string("video/x-raw,format=RGB")
        elements["capsfilter_appsink"].set_property("caps", caps_visualisation)

        return elements

    def construct_pipeline(self) -> Gst.Pipeline:
        """Construct the GStreamer pipeline.

        Creates a pipeline that converts between GRAY16_LE and GRAY16_BE formats
        for proper thermal data recording.

        Returns
        -------
        Gst.Pipeline
            Configured GStreamer pipeline for thermal camera
        """
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
                elements["capsfilter_16_le"],
                self.tee,
            ]
        ):
            self.src.link(elements["videorate"])
            elements["videorate"].link(elements["capsfilter_16_le"])
            elements["capsfilter_16_le"].link(self.tee)

        # Link recording branch
        if all(
            x is not None
            for x in [
                self.tee,
                self.queue_recording,
                elements["videoconvert_recording"],
                elements["capsfilter16_be"],
                self.sink,
            ]
        ):
            self.tee.link(self.queue_recording)
            self.queue_recording.link(elements["videoconvert_recording"])
            elements["videoconvert_recording"].link(elements["capsfilter16_be"])
            elements["capsfilter16_be"].link(self.sink)

        # Link appsink branch
        if all(
            x is not None
            for x in [
                elements["queue_appsink"],
                elements["videoconvert_visualisation"],
                elements["visualisation"],
                elements["videoconvert_appsink"],
                elements["capsfilter_appsink"],
                self.appsink,
            ]
        ):
            self.tee.link(elements["queue_appsink"])
            elements["queue_appsink"].link(elements["videoconvert_visualisation"])
            elements["videoconvert_visualisation"].link(elements["visualisation"])
            elements["visualisation"].link(elements["videoconvert_appsink"])
            elements["videoconvert_appsink"].link(elements["capsfilter_appsink"])
            elements["capsfilter_appsink"].link(self.appsink)
            self.appsink.connect("new-sample", self.callback)
