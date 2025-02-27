"""GStreamer pipeline initialization and common imports."""

import logging

from .pipeline_abc import BasePipeline

# get or connect to existing logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    from gi.repository import Gst

    from .rgb_pipeline import RGBPipeline
    from .thermal_pipeline import ThermalPipeline
except ImportError:
    logger.warning(
        "GStreamer Python bindings not found. Please install gstreamer1.0-python3"
    )

    class RGBPipeline(BasePipeline):
        """Dummy RGB pipeline implementation."""

    class ThermalPipeline(BasePipeline):  # type: ignore
        """Dummy thermal pipeline implementation."""


__all__ = ["Gst", "RGBPipeline", "ThermalPipeline"]
