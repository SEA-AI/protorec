"""Thermal camera pipeline implementation for video recording.

This module provides the ThermalPipeline class that implements a GStreamer pipeline
for recording from thermal cameras with 16-bit grayscale output.
"""

from protorec.pipelines import Gst
from protorec.pipelines.pipeline import CameraPipeline


class ThermalPipeline(CameraPipeline):
    """Pipeline implementation for thermal cameras.

    This class implements a GStreamer pipeline for recording from thermal cameras,
    handling 16-bit grayscale format conversion and recording.
    """

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
        elements = {
            "videorate": Gst.ElementFactory.make("videorate", "videorate"),
            "capsfilter_16_le": Gst.ElementFactory.make(
                "capsfilter", "capsfilter16_le"
            ),
            "videoconvert": Gst.ElementFactory.make("videoconvert", "videoconvert"),
            "capsfilter16_be": Gst.ElementFactory.make("capsfilter", "capsfilter16_be"),
        }

        # Check if elements were created successfully
        failed_elements = [
            name for name, element in elements.items() if element is None
        ]
        if failed_elements:
            raise RuntimeError(
                f"Failed to create elements: {', '.join(failed_elements)}"
            )

        # Configure capsfilters
        caps_16_le = Gst.Caps.from_string(
            f"video/x-raw,framerate={self.framerate}/1,format=GRAY16_LE"
        )
        elements["capsfilter_16_le"].set_property("caps", caps_16_le)

        caps_16_be = Gst.Caps.from_string(
            f"video/x-raw,framerate={self.framerate}/1,format=GRAY16_BE"
        )
        elements["capsfilter16_be"].set_property("caps", caps_16_be)

        # Add elements to pipeline
        for element in [self.src, *elements.values(), self.sink]:
            pipeline.add(element)

        # Link elements
        self.src.link(elements["videorate"])
        elements["videorate"].link(elements["capsfilter_16_le"])
        elements["capsfilter_16_le"].link(elements["videoconvert"])
        elements["videoconvert"].link(elements["capsfilter16_be"])
        elements["capsfilter16_be"].link(self.sink)

        return pipeline
