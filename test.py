import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

import thread
import time
import sys
GObject.threads_init()
Gst.init(None)

CLI = 'rtmpsrc location=rtmp://test-ingest.stageten.tv/vod/musicalThangs-1495670282.flv name=vsrc1 ! flvdemux name=flv1 flv1.video ! queue ! i.sink_0 rtmpsrc name=vsrc2 location=rtmp://test-ingest.stageten.tv/vod/musicalThangs-1493251641.flv ! flvdemux name=flv2 flv2.video ! queue ! i.sink_1 input-selector sync-mode="active-segment" sync-streams=true cache-buffers=false name=i i. ! queue ! flvout. audiotestsrc name=testtone freq=100 volume=0.0 ! audio/x-raw,format=S8,rate=44100,channels=1,depth=16,signed=true,endianess=1234,width=16 ! queue ! audiorate ! audioconvert ! audioresample ! queue ! adder name=audioadder is-live=true  ! queue ! audioconvert ! queue ! audioresample ! queue ! voaacenc bitrate=128000 ! queue ! aacparse ! audio/mpeg,mpegversion=4,stream-format=raw ! queue ! flvout. flvmux name=flvout streamable=true ! queue ! rtmpsink location="rtmp://a.rtmp.youtube.com/live2/hvcd-ssyb-esqr-2x2m" sync=false'

pipeline=Gst.parse_launch(CLI)
selector = pipeline.get_by_name("i")

global new_pad, probe, selector,pipeline
new_pad = selector.get_static_pad("sink_1")
selector.set_property("active-pad", new_pad)
print(new_pad)
caps = new_pad.query_caps(None)
structure_name = caps.to_string()
print(structure_name)
pipeline.set_state(Gst.State.PLAYING)


print "Waiting 15 seconds"
time.sleep(20)


def gst_buffer_is_keyframe(this_pad,probe_info):
	global new_pad, probe, selector,pipeline
	
	buf = probe_info.get_buffer()
	delta = not (buf.mini_object.flags & Gst.BufferFlags.DELTA_UNIT)
	if delta:
		selector.set_property("active-pad", new_pad)
		new_pad.remove_probe(probe)
		print "KEYFRAME -- switching"
	return Gst.PadProbeReturn.OK

while True:
	print "Requesting Switch"
	new_pad = selector.get_static_pad("sink_0")
	probe = new_pad.add_probe(Gst.PadProbeType.BUFFER, gst_buffer_is_keyframe)
	print "Waiting 15 seconds"
	time.sleep(15)
	print "Requesting Switch"
	new_pad = selector.get_static_pad("sink_1")
	probe = new_pad.add_probe(Gst.PadProbeType.BUFFER, gst_buffer_is_keyframe)
	print "Waiting 15 seconds"
	time.sleep(15)

