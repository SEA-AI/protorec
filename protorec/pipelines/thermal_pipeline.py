from gi.repository import Gst

from protorec.pipelines.pipeline import CameraPipeline


class ThermalPipeline(CameraPipeline):
    def __init__(self, config, framerate=30):
        super().__init__(config, framerate)

    def construct_pipeline(self):
        pipeline = Gst.Pipeline.new("pipeline" + self.config["name"])

        self.src = self.get_src()
        self.sink = self.get_sink()

        videorate = Gst.ElementFactory.make("videorate", "videorate")
        capsfilter_16_le = Gst.ElementFactory.make("capsfilter", "capsfilter16_le")
        caps_16_le = Gst.Caps.from_string(
            f"video/x-raw,framerate={self.framerate}/1,format=GRAY16_LE"
        )
        capsfilter_16_le.set_property("caps", caps_16_le)
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        capsfilter16_be = Gst.ElementFactory.make("capsfilter", "capsfilter16_be")
        caps_16_be = Gst.Caps.from_string(
            f"video/x-raw,framerate={self.framerate}/1,format=GRAY16_BE"
        )
        capsfilter16_be.set_property("caps", caps_16_be)

        pipeline.add(self.src)
        pipeline.add(videorate)
        pipeline.add(capsfilter_16_le)
        pipeline.add(videoconvert)
        pipeline.add(capsfilter16_be)
        pipeline.add(self.sink)

        self.src.link(videorate)
        videorate.link(capsfilter_16_le)
        capsfilter_16_le.link(videoconvert)
        videoconvert.link(capsfilter16_be)
        capsfilter16_be.link(self.sink)

        return pipeline
