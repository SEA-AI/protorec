import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
from copy import deepcopy

import numpy as np
from gi.repository import Gst

from protorec.pipelines.pipeline import CameraPipeline


class RGBPipeline(CameraPipeline):
    def __init__(self, config, framerate=30):
        super().__init__(config, framerate)
        self._frame = None

    def construct_pipeline(self):
        """
        Construct the pipeline. One appsink branch and one recording branch
        """
        pipeline = Gst.Pipeline.new("pipeline" + self.config["name"])

        self.src = self.get_src()
        self.sink = self.get_sink()

        # ---------------------- Make Elements

        # common
        videorate = Gst.ElementFactory.make("videorate", "videorate")
        capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        caps = Gst.Caps.from_string(
            f"video/x-raw(memory:NVMM),framerate={self.framerate}/1"
        )
        capsfilter.set_property("caps", caps)

        # tee
        self.tee = Gst.ElementFactory.make("tee", "tee")
        self.queue_recording = Gst.ElementFactory.make("queue", "queue_recording")
        self.queue_recording.set_property("max-size-buffers", 5)
        self.queue_recording.set_property("leaky", 2)
        queue_appsink = Gst.ElementFactory.make("queue", "queue_appsink")
        queue_appsink.set_property("max-size-buffers", 5)
        queue_appsink.set_property("leaky", 2)

        # recording
        videoconvert = Gst.ElementFactory.make("nvvidconv", "nvvidconv")
        jpegenc = Gst.ElementFactory.make("nvjpegenc", "nvjpegenc")
        avimux = Gst.ElementFactory.make("avimux", "avimux")

        # appsink
        nvidconv_appsink = Gst.ElementFactory.make("nvvidconv", "nvvidconv_appsink")
        videoconvert_appsink = Gst.ElementFactory.make(
            "videoconvert", "videoconvert_appsink"
        )
        videorate_appsink = Gst.ElementFactory.make("videorate", "videorate_appsink")
        capsfilter_appsink = Gst.ElementFactory.make("capsfilter", "capsfilter_appsink")
        caps_appsink = Gst.Caps.from_string("video/x-raw,format=BGR")
        capsfilter_appsink.set_property("caps", caps_appsink)
        self.appsink = Gst.ElementFactory.make("appsink", "appsink")
        self.appsink.set_property("emit-signals", True)
        self.appsink.set_property("sync", True)
        self.appsink.set_property("max-buffers", 1)
        self.appsink.set_property("drop", True)

        # ---------------------- Add Elements

        # common
        pipeline.add(self.src)
        pipeline.add(videorate)
        pipeline.add(capsfilter)
        pipeline.add(videoconvert)

        # tee
        pipeline.add(self.tee)
        pipeline.add(self.queue_recording)
        pipeline.add(queue_appsink)

        # recording
        pipeline.add(jpegenc)
        pipeline.add(avimux)
        pipeline.add(self.sink)

        # appsink
        pipeline.add(nvidconv_appsink)
        pipeline.add(videoconvert_appsink)
        pipeline.add(capsfilter_appsink)
        pipeline.add(self.appsink)

        # ---------------------- Link Elements

        # common
        self.src.link(videorate)
        videorate.link(capsfilter)
        capsfilter.link(videoconvert)
        videoconvert.link(self.tee)

        # tee
        self.tee.link(self.queue_recording)
        self.tee.link(queue_appsink)

        # recording
        self.queue_recording.link(jpegenc)
        jpegenc.link(avimux)
        avimux.link(self.sink)

        # #appsink
        queue_appsink.link(nvidconv_appsink)
        nvidconv_appsink.link(videoconvert_appsink)
        videoconvert_appsink.link(capsfilter_appsink)
        capsfilter_appsink.link(self.appsink)
        self.appsink.connect("new-sample", self.callback)

        return pipeline

    def callback(self, sink):
        """
        Callback to get the frame from the pipeline
        """
        sample = sink.emit("pull-sample")
        if not sample:
            return Gst.FlowReturn.ERROR

        buffer = sample.get_buffer()
        if not buffer:
            return Gst.FlowReturn.ERROR

        new_frame = self.gst_to_numpy(sample)
        self._frame = new_frame

        # Explicitly release the sample and buffer
        del sample
        del buffer

        return Gst.FlowReturn.OK

    def get_frame(self):
        """
        Get the frame from the pipeline
        """
        return self._frame

    @staticmethod
    def gst_to_numpy(sample):
        """
        Transform byte array into np array
        Args:
            sample (TYPE): Description
        Returns:
            TYPE: Description
        """
        buf = sample.get_buffer()
        caps = sample.get_caps()

        format = caps.get_structure(0).get_value("format")
        height = caps.get_structure(0).get_value("height")
        width = caps.get_structure(0).get_value("width")

        array = np.ndarray(
            (
                caps.get_structure(0).get_value("height"),
                caps.get_structure(0).get_value("width"),
                3,
            ),
            buffer=buf.extract_dup(0, buf.get_size()),
            dtype=np.uint8,
        )

        return deepcopy(array)  # deepcopy, seems to avoid segmentation fault

    def stop(self):
        """
        Stop the pipeline and set state to NULL

        Known issue: when using pylonsrc, jetson device may crash
        """
        self.pipeline.send_event(Gst.Event.new_eos())
        self.pipeline.set_state(Gst.State.NULL)
        self._frame = None
