"""RGB camera pipeline implementation for video recording.

This module provides the RGBPipeline class that implements a GStreamer pipeline
for recording from RGB/color cameras with NVIDIA hardware acceleration.
"""

from typing import List

from protorec.pipelines import Gst
from protorec.pipelines.pipeline import CameraPipeline


class RGBPipeline(CameraPipeline):
    """Pipeline implementation for RGB/color cameras.

    This class implements a GStreamer pipeline for recording from color cameras,
    with support for both recording to file and real-time frame access through
    an appsink element.
    """

    def _create_source_chain(self) -> List[Gst.Element]:
        """Create the rate limiting and NVMM conversion elements.

        Returns
        -------
        List[Gst.Element]
            videorate, NVMM capsfilter and nvvidconv elements
        """
        caps = Gst.Caps.from_string(
            f"video/x-raw(memory:NVMM),framerate={self.framerate}/1"
        )
        return [
            self._make_element("videorate", "videorate"),
            self._make_element("capsfilter", "capsfilter", {"caps": caps}),
            self._make_element("nvvidconv", "nvvidconv"),
        ]

    def _create_recording_chain(self) -> List[Gst.Element]:
        """Create the MJPEG encoding elements.

        Returns
        -------
        List[Gst.Element]
            nvjpegenc and avimux elements
        """
        return [
            self._make_element("nvjpegenc", "nvjpegenc"),
            self._make_element("avimux", "avimux"),
        ]

    def _create_appsink_chain(self) -> List[Gst.Element]:
        """Create the BGR conversion elements.

        Returns
        -------
        List[Gst.Element]
            nvvidconv, videoconvert and BGR capsfilter elements
        """
        caps_appsink = Gst.Caps.from_string("video/x-raw,format=BGR")
        return [
            self._make_element("nvvidconv", "nvvidconv_appsink"),
            self._make_element("videoconvert", "videoconvert_appsink"),
            self._make_element(
                "capsfilter", "capsfilter_appsink", {"caps": caps_appsink}
            ),
        ]
