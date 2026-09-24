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
    def run(self) -> None:
        """Run the pipeline."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the pipeline."""

    @abc.abstractmethod
    def is_playing(self) -> bool:
        """Check if pipeline is playing."""

    @abc.abstractmethod
    def is_stopped(self) -> bool:
        """Check if pipeline is stopped."""

    @abc.abstractmethod
    def set_dir(self, dir_path: str) -> None:
        """Set output directory."""
