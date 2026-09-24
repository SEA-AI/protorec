"""Thermal camera pipeline implementation for video recording.

This module provides the ThermalPipeline class that implements a GStreamer pipeline
for recording from thermal cameras with 16-bit grayscale output.
"""

from typing import List

from protorec.pipelines import Gst
from protorec.pipelines.pipeline import CameraPipeline


class ThermalPipeline(CameraPipeline):
    """Pipeline implementation for thermal cameras.

    This class implements a GStreamer pipeline for recording from thermal cameras,
    converting GRAY16_LE to GRAY16_BE for recording and rendering a CLAHE
    visualisation for streaming.
    """

    def _create_source_chain(self) -> List[Gst.Element]:
        """Create the rate limiting elements.

        Returns
        -------
        List[Gst.Element]
            videorate and GRAY16_LE capsfilter elements
        """
        caps_16_le = Gst.Caps.from_string(
            f"video/x-raw,framerate={self.framerate}/1,format=GRAY16_LE"
        )
        return [
            self._make_element("videorate", "videorate"),
            self._make_element("capsfilter", "capsfilter16_le", {"caps": caps_16_le}),
        ]

    def _create_recording_chain(self) -> List[Gst.Element]:
        """Create the GRAY16_BE conversion elements.

        Returns
        -------
        List[Gst.Element]
            videoconvert and GRAY16_BE capsfilter elements
        """
        caps_16_be = Gst.Caps.from_string(
            f"video/x-raw,framerate={self.framerate}/1,format=GRAY16_BE"
        )
        return [
            self._make_element("videoconvert", "videoconvert_recording"),
            self._make_element("capsfilter", "capsfilter16_be", {"caps": caps_16_be}),
        ]

    def _create_appsink_chain(self) -> List[Gst.Element]:
        """Create the visualisation elements.

        Returns
        -------
        List[Gst.Element]
            videoconvert, visualisation, videoconvert and RGB capsfilter elements
        """
        caps_visualisation = Gst.Caps.from_string("video/x-raw,format=RGB")
        return [
            self._make_element("videoconvert", "videoconvert_visualisation"),
            self._make_element(
                "visualisation",
                "visualisation",
                {
                    "display_mode": "clahe",
                    "display-linear-cutoff-frequency": 0.5,
                    "display-lower-saturation-thr": 15000,
                    "display-upper-saturation-thr": 28000,
                },
            ),
            self._make_element("videoconvert", "videoconvert_appsink"),
            self._make_element(
                "capsfilter", "capsfilter_appsink", {"caps": caps_visualisation}
            ),
        ]
