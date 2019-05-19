import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
import threading
import time
import sys

GObject.threads_init()
Gst.init(None)


Gst.debug_set_active(True)
Gst.debug_set_default_threshold(3)

CLI = 'videotestsrc pattern=snow is-live=TRUE name=s1 ! queue ! capsfilter name=s2 caps="video/x-raw,format=(string)I420,width=(int)640,height=(int)360,framerate=(fraction)30/1" ! queue ! interpipesink name="sink1" forward-events=TRUE videotestsrc  is-live=TRUE name=s11 ! queue ! capsfilter name=s12 caps="video/x-raw,format=(string)I420,width=(int)640,height=(int)360,framerate=(fraction)30/1" ! queue ! interpipesink forward-events=TRUE name="sink2" interpipesrc name="source1" listen-to="sink1" is-live=TRUE ! queue ! capsfilter name=s3 caps="video/x-raw,format=(string)I420,width=(int)640,height=(int)360,framerate=(fraction)30/1" ! queue max-size-bytes=0 max-size-time=0 max-size-buffers=0 ! x264enc cabac=false aud=true tune=zerolatency byte-stream=false sliced-threads=true threads=4 speed-preset=1 bitrate=2000 key-int-max=20 bframes=0 ! queue ! h264parse ! queue ! video/x-h264,profile=main ! queue ! mux. audiotestsrc name=testtone freq=100 volume=0.0 ! audio/x-raw,format=S8,rate=44100,channels=1,depth=16,signed=true,endianess=1234,width=16 ! audiorate ! audioconvert ! audioresample ! adder name=audioadder is-live=true ! audioconvert ! audioresample ! queue ! voaacenc bitrate=128000 ! aacparse ! audio/mpeg,mpegversion=4,stream-format=raw ! queue ! flvmux streamable=true name=mux ! queue ! rtmpsink location="rtmp://test-ingest.stageten.tv/live/test" sync=false'

pipline1=Gst.parse_launch(CLI)
pipline1.set_state(Gst.State.PLAYING)
outputsrc = pipline1.get_by_name("source1")

while 1:
        print("Enter to change inputs")
        input1 = input()
        outputsrc.set_property('listen-to','sink2')
        print("Enter to change inputs")
        input1 = input()
        outputsrc.set_property('listen-to','sink1')

