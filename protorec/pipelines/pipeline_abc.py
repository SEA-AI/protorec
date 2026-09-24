"""Abstract base class for camera pipeline handling."""

import abc


class BasePipeline(abc.ABC):
    """Abstract base class for camera pipeline handling.

    This class provides the basic interface that all pipeline implementations
    must follow.
    """

    @abc.abstractmethod
    def construct_pipeline(self):
        """Construct the GStreamer pipeline."""

    @abc.abstractmethod
    def run(self) -> bool:
        """Run the pipeline and report whether it started."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the pipeline."""

    @abc.abstractmethod
    def start_preview(self) -> None:
        """Start streaming frames without recording."""

    @abc.abstractmethod
    def stop_preview(self) -> None:
        """Stop streaming frames without recording."""

    @abc.abstractmethod
    def is_playing(self) -> bool:
        """Check if pipeline is playing."""

    @abc.abstractmethod
    def is_stopped(self) -> bool:
        """Check if pipeline is stopped."""

    @abc.abstractmethod
    def set_dir(self, dir_path: str) -> None:
        """Set output directory."""
