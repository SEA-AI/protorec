"""GStreamer pipeline initialization and common imports."""

try:
    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    from gi.repository import Gst
except ImportError as e:
    raise ImportError(
        "GStreamer Python bindings not found. Please install gstreamer1.0-python3"
    ) from e

__all__ = ["Gst"]
