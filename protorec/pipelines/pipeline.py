"""Base camera pipeline class for video recording.

This module provides the base CameraPipeline class that handles GStreamer pipeline
setup and control for video recording from different camera types.
"""

import logging
import os
from copy import deepcopy
from typing import Any, Dict, List, Optional

import numpy as np

from . import Gst
from .pipeline_abc import BasePipeline

logger = logging.getLogger(__name__)


class CameraPipeline(BasePipeline):
    """Base class for camera pipeline handling.

    This class assembles two GStreamer pipelines from element chains that
    subclasses provide:

    - Recording: ``src -> source chain -> tee``, where the tee feeds both
      ``queue -> recording chain -> filesink`` and ``queue -> appsink chain ->
      appsink``.
    - Preview: ``src -> source chain -> queue -> appsink chain -> appsink``,
      which streams frames without writing to disk.

    Both pipelines open the same camera, so only one of them may run at a time.
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
        self.sink: Optional[Gst.Element] = None
        self._frame: Optional[np.ndarray] = None
        self.pipeline: Gst.Pipeline = self.construct_pipeline()
        self.preview_pipeline: Gst.Pipeline = self.construct_preview_pipeline()
        self.terminate = False
        self.dir = "."
        self.format = config["format"]

    def _create_source_chain(self) -> List[Gst.Element]:
        """Create the elements between the source and the tee.

        Returns
        -------
        List[Gst.Element]
            Elements to link in order after the source

        Raises
        ------
        NotImplementedError
            If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _create_source_chain()")

    def _create_recording_chain(self) -> List[Gst.Element]:
        """Create the elements between the recording queue and the filesink.

        Returns
        -------
        List[Gst.Element]
            Elements to link in order before the filesink

        Raises
        ------
        NotImplementedError
            If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _create_recording_chain()")

    def _create_appsink_chain(self) -> List[Gst.Element]:
        """Create the elements between the appsink queue and the appsink.

        Returns
        -------
        List[Gst.Element]
            Elements to link in order before the appsink

        Raises
        ------
        NotImplementedError
            If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _create_appsink_chain()")

    def construct_pipeline(self) -> Gst.Pipeline:
        """Construct the recording pipeline.

        Returns
        -------
        Gst.Pipeline
            Pipeline that records to the filesink and streams to the appsink
        """
        pipeline = Gst.Pipeline.new("pipeline" + self.config["name"])
        tee = self._make_element("tee", "tee")
        self.sink = self.get_sink()

        self._link_chain(pipeline, [self.get_src(), *self._create_source_chain(), tee])
        self._link_chain(
            pipeline,
            [
                tee,
                self._make_queue("queue_recording"),
                *self._create_recording_chain(),
                self.sink,
            ],
        )
        self._link_chain(
            pipeline,
            [
                tee,
                self._make_queue("queue_appsink"),
                *self._create_appsink_chain(),
                self.get_appsink(),
            ],
        )
        return pipeline

    def construct_preview_pipeline(self) -> Gst.Pipeline:
        """Construct the preview pipeline.

        Returns
        -------
        Gst.Pipeline
            Pipeline that only streams to the appsink
        """
        pipeline = Gst.Pipeline.new("preview" + self.config["name"])
        self._link_chain(
            pipeline,
            [
                self.get_src(),
                *self._create_source_chain(),
                self._make_queue("queue_appsink"),
                *self._create_appsink_chain(),
                self.get_appsink(),
            ],
        )
        return pipeline

    @staticmethod
    def _make_element(
        factory: str, name: str, properties: Optional[Dict[str, Any]] = None
    ) -> Gst.Element:
        """Create an element and apply properties.

        Parameters
        ----------
        factory : str
            GStreamer element factory name
        name : str
            Element name, unique within its pipeline
        properties : Optional[Dict[str, Any]], optional
            Element properties to set, by default None

        Returns
        -------
        Gst.Element
            Configured element

        Raises
        ------
        RuntimeError
            If the element cannot be created
        """
        element = Gst.ElementFactory.make(factory, name)
        if element is None:
            raise RuntimeError(f"Could not create {factory} element")

        for key, value in (properties or {}).items():
            element.set_property(key, value)
        return element

    def _make_queue(self, name: str) -> Gst.Element:
        """Create a leaky queue that drops old buffers when full.

        Parameters
        ----------
        name : str
            Element name, unique within its pipeline

        Returns
        -------
        Gst.Element
            Configured queue element
        """
        return self._make_element("queue", name, {"max-size-buffers": 5, "leaky": 2})

    @staticmethod
    def _link_chain(pipeline: Gst.Pipeline, chain: List[Gst.Element]) -> None:
        """Add elements to the pipeline and link them in order.

        Elements already in the pipeline, such as a tee shared by several
        branches, are linked without being added again.

        Parameters
        ----------
        pipeline : Gst.Pipeline
            Pipeline to add the elements to
        chain : List[Gst.Element]
            Elements to link, from upstream to downstream

        Raises
        ------
        RuntimeError
            If two consecutive elements cannot be linked
        """
        for element in chain:
            if element.get_parent() is None:
                pipeline.add(element)

        for upstream, downstream in zip(chain, chain[1:]):
            if not upstream.link(downstream):
                raise RuntimeError(
                    f"Could not link {upstream.get_name()} to {downstream.get_name()}"
                )

    def get_src(self) -> Gst.Element:
        """Get source element and apply properties.

        Returns
        -------
        Gst.Element
            Configured source element
        """
        return self._make_element(
            self.config["element"], "src", self.config["properties"]
        )

    def get_sink(self) -> Gst.Element:
        """Get sink element.

        Returns
        -------
        Gst.Element
            Configured filesink element
        """
        return self._make_element("filesink", "filesink")

    def get_appsink(self) -> Gst.Element:
        """Get appsink element that keeps only the latest frame.

        Returns
        -------
        Gst.Element
            Configured appsink element connected to the frame callback
        """
        appsink = self._make_element(
            "appsink",
            "appsink",
            {"emit-signals": True, "sync": True, "max-buffers": 1, "drop": True},
        )
        appsink.connect("new-sample", self.callback)
        return appsink

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
        self._frame = None

    def start_preview(self) -> None:
        """Start streaming frames to the appsink without recording."""
        ret = self.preview_pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.warning("Could not start preview for %s", self.config["name"])
            self.preview_pipeline.set_state(Gst.State.NULL)

    def stop_preview(self) -> None:
        """Stop the preview pipeline and release the camera."""
        self.preview_pipeline.set_state(Gst.State.NULL)
        self._frame = None

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
