import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst

from contextlib import contextmanager
import asyncio
import time
import os

class CameraPipeline: 
    def __init__(self, config, framerate=30): 
        self.config = config 
        self.framerate = framerate   
        self.src = None
        self.sink = None
        self.pipeline = self.construct_pipeline() 
        self.terminate = False
        self.dir = "."
        self.format = config["format"]

    def get_src(self):
        """
        Get source element and apply properties
        """

        src = Gst.ElementFactory.make(self.config["element"], "src")
        for key, value in self.config["properties"].items():
            src.set_property(key, value)
        return src

    def get_sink(self):
        """
        Get sink element
        """

        sink = Gst.ElementFactory.make("filesink", "filesink")
        return sink

    def run(self):
        """
        Run the pipeline and set the sink location
        """
        self.sink.set_property("location", os.path.join(self.dir, self.config["name"]+self.format))
        self.pipeline.set_state(Gst.State.READY)
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        """
        Stop the pipeline and set state to NULL
        """
        self.pipeline.send_event(Gst.Event.new_eos())
        self.pipeline.set_state(Gst.State.NULL)

    def is_playing(self):
        """
        Check if the pipeline is playing
        """
        state_change_return, state, pending_state = self.pipeline.get_state(timeout=Gst.CLOCK_TIME_NONE)
        return state == Gst.State.PLAYING

    def is_stopped(self):
        """
        Check if the pipeline is stopped
        """
        state_change_return, state, pending_state = self.pipeline.get_state(timeout=Gst.CLOCK_TIME_NONE)
        return state == Gst.State.NULL
    
    def set_dir(self, dir):
        """
        Set the directory to save the video
        """
        self.dir = dir