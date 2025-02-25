"""RGB camera pipeline implementation for video recording.

This module provides the RGBPipeline class that implements a GStreamer pipeline
for recording from RGB/color cameras with NVIDIA hardware acceleration.
"""

from copy import deepcopy
from typing import Any, Dict, Optional

import numpy as np

try:
    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    from gi.repository import Gst
except ImportError as e:
    raise ImportError(
        "GStreamer Python bindings not found. Please install gstreamer1.0-python3"
    ) from e

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

        # Recording elements
        elements["videoconvert"] = Gst.ElementFactory.make("nvvidconv", "nvvidconv")
        elements["jpegenc"] = Gst.ElementFactory.make("nvjpegenc", "nvjpegenc")
        elements["avimux"] = Gst.ElementFactory.make("avimux", "avimux")

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
        if all(
            x is not None
            for x in [
                self.tee,
                self.queue_recording,
                elements["jpegenc"],
                elements["avimux"],
                self.sink,
            ]
        ):
            self.tee.link(self.queue_recording)
            self.queue_recording.link(elements["jpegenc"])
            elements["jpegenc"].link(elements["avimux"])
            elements["avimux"].link(self.sink)

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

    def callback(self, sink: Gst.Element) -> Gst.FlowReturn:
        """Process new frames from the pipeline.

        Parameters
        ----------
        sink : Gst.Element
            Appsink element that emitted the new-sample signal

        Returns
        -------
        Gst.FlowReturn
            GST_FLOW_OK if frame was processed successfully
        """
        sample = sink.emit("pull-sample")
        if not sample:
            return Gst.FlowReturn.ERROR

        buffer = sample.get_buffer()
        if not buffer:
            return Gst.FlowReturn.ERROR

        new_frame = self.gst_to_numpy(sample)
        self._frame = new_frame

        return Gst.FlowReturn.OK

    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame from the pipeline.

        Returns
        -------
        Optional[np.ndarray]
            Latest frame as numpy array, or None if no frame is available
        """
        return self._frame

    @staticmethod
    def gst_to_numpy(sample: Gst.Sample) -> np.ndarray:
        """Convert GStreamer sample to numpy array.

        Parameters
        ----------
        sample : Gst.Sample
            GStreamer sample containing video frame

        Returns
        -------
        np.ndarray
            Video frame as numpy array
        """
        buf = sample.get_buffer()
        caps = sample.get_caps()
        struct = caps.get_structure(0)

        height = struct.get_value("height")
        width = struct.get_value("width")

        array = np.ndarray(
            (height, width, 3),
            buffer=buf.extract_dup(0, buf.get_size()),
            dtype=np.uint8,
        )

        return deepcopy(array)

    def stop(self) -> None:
        """Stop the pipeline and clean up resources.

        Note: When using pylonsrc, the Jetson device may crash.
        """
        super().stop()
        self._frame = None
