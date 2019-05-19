## should support both Python 2.7 and Python 3.5

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
try: import thread
except: import _thread as thread
import time
import sys
try: from urllib.request import urlopen
except: from urllib import urlopen
try: from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
except: from http.server import BaseHTTPRequestHandler, HTTPServer
try: from SocketServer import ThreadingMixIn
except: from socketserver import ThreadingMixIn
try: from urlparse import urlparse
except: from urllib import parse
try: import simplejson as json
except ImportError: import json

import youtube_dl

global ydl
ydl = youtube_dl.YoutubeDL({'outtmpl': '%(id)s%(ext)s'})

GObject.threads_init()
Gst.init(None)

Gst.debug_set_active(True)
Gst.debug_set_default_threshold(3)

widthout = 1280  # output resolution.
heightout = 720
fpsout = 30
global pad0a, pad0v, pad1a, pad1v, decodebin, audiodecodebin

def gen_cb(a, b, *c):
    return Gst.PadProbeReturn.OK

class apiHandler(BaseHTTPRequestHandler):  ## a basic webserver.
	def do_HEAD(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
	def decoder_callback(self, dec, pad):
		global switcher, mainpipe, audioswitcher
		global pad0a, pad0v, pad1a, pad1v
		print("callback")
		caps = pad.query_caps(None)
		structure_name = caps.to_string()
		if structure_name.startswith("video"):
			print("video")
			pad1v = pad
			init = switcher.get_static_pad("sink_0")
			switcher.set_property('active-pad', init)
			switchersink = switcher.get_static_pad("sink_1")
			try:
				pad.link(switchersink)
			except:
				switchersink = switcher.get_request_pad("sink_%u")
				pad.link(switchersink)
			dec.set_state(Gst.State.PLAYING)
			print("video playing")
			return True
		elif structure_name.startswith("audio"):
                        pad1a = pad
                        print("audio")
                        init = audioswitcher.get_static_pad("sink_0")
                        audioswitcher.set_property('active-pad', init)
                        switchersink = switcher.get_static_pad("sink_1")
                        try:
                                pad.link(audioswitchersink)
                        except:
                                audioswitchersink = audioswitcher.get_request_pad("sink_%u")
                                pad.link(audioswitchersink)
                        dec.set_state(Gst.State.PLAYING)
                        print("audio playing")
                        return True

	def do_GET(self): ## useful for single-stream shot updates
		global mainpipe, ydl
		global pad0a, pad0v, pad1a, pad1v, decodebin, audiodecodebin
		o = parse.urlparse(self.path)
		o = dict(parse.parse_qsl(o.query))
		if ("src" in o):
			print(o['src'])
			
			decodebin = Gst.ElementFactory.make("uridecodebin")
			mainpipe.add(decodebin)
			decodebin.connect("pad-added", self.decoder_callback)
			decodebin.set_property('uri', o['src'])

			decodebin.set_state(Gst.State.PAUSED)

			self.send_response(200)
			self.send_header('Content-type','text/html')
			self.send_header('Access-Control-Allow-Origin','*')
			self.end_headers()
			return
		elif ("start" in o):
			audioswitchersink = audioswitcher.get_static_pad("sink_1")
			audioswitcher.set_property('active-pad', audioswitchersink)
			switchersink = switcher.get_static_pad("sink_1")
			print(mainpipe.query_position(Gst.Format.TIME))
			print(pad1v.query_position(Gst.Format.TIME))
			print(pad1a.query_position(Gst.Format.TIME))
			audiodecodebin.set_state(Gst.State.PLAYING)
			decodebin.set_state(Gst.State.PLAYING)
			#pad1a.set_offset(pad1a.query_position(Gst.Format.TIME)[1] - mainpipe.query_position(Gst.Format.TIME)[1])
			#pad1v.set_offset(pad1v.query_position(Gst.Format.TIME)[1] - mainpipe.query_position(Gst.Format.TIME)[1])
			#switcher.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0 * Gst.SECOND)
			switcher.set_property('active-pad', switchersink)
		elif ("stop" in o):
                        audioswitchersink = audioswitcher.get_static_pad("sink_0")
                        audioswitcher.set_property('active-pad', audioswitchersink)
                        switchersink = switcher.get_static_pad("sink_0")
                        switcher.set_property('active-pad', switchersink)
		elif ("v" in o):
			print(o['v'])
			with ydl:
				result = ydl.extract_info('http://www.youtube.com/watch?v='+o['v'], download=False)
			if 'entries' in result:
				# Can be a playlist or a list of videos
				video = result['entries'][0]
			else:
				# Just a video
				video = result
			#print(video)
			src=None
			asrc=None
			for i in video['requested_formats']:
				#print(i['format'])
				print(i['url'])
				print(i['vcodec'])
				print(i['acodec'])
				if (i['vcodec']!="none"):
					src = i['url']
				elif (i['acodec']!="none"):
                                        asrc = i['url']
			print("***********")
			print(src)
			print(asrc)
			if src!=None:
				decodebin = Gst.ElementFactory.make("uridecodebin")
				mainpipe.add(decodebin)
				decodebin.connect("pad-added", self.decoder_callback)
				decodebin.set_property('use-buffering', 'TRUE')
				decodebin.set_property('uri', src)
				decodebin.set_state(Gst.State.PAUSED)

			if asrc!=None:
                                audiodecodebin = Gst.ElementFactory.make("uridecodebin")
                                mainpipe.add(audiodecodebin)
                                audiodecodebin.connect("pad-added", self.decoder_callback)
                                audiodecodebin.set_property('uri', asrc)
                                audiodecodebin.set_property('use-buffering', 'TRUE')
                                audiodecodebin.set_state(Gst.State.PAUSED)

			self.send_response(200)
			self.send_header('Content-type','text/html')
			self.send_header('Access-Control-Allow-Origin','*')
			self.end_headers()
			return

		else:
			self.send_response(200)
			self.send_header('Content-type','text/html')
			self.send_header('Access-Control-Allow-Origin','*')
			self.end_headers()
			print("unknown HTTP request inbound")
			return
			
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	pass

CLI = 'videotestsrc ! video/x-raw,interlace-mode=progressive,format=I420,width='+str(widthout)+',height='+str(heightout)+',framerate=(fraction)30/1,pixel-aspect-ratio=(fraction)1/1 ! switch.sink_0 input-selector cache-buffers=TRUE sync-mode="clock" name=switch ! queue ! videoconvert ! videoscale ! videorate ! queue ! capsfilter caps="video/x-raw,format=I420,width='+str(widthout)+',height='+str(heightout)+',framerate=(fraction)30/1" ! timeoverlay halignment=right valignment=bottom text="Stream time:" shaded-background=true font-desc="Sans, 32" ! queue ! x264enc cabac=false aud=true tune=zerolatency byte-stream=false sliced-threads=true threads=4 speed-preset=1 bitrate=2000 key-int-max=20 bframes=0 ! queue ! h264parse ! queue ! video/x-h264,profile=main ! queue ! mux. audiotestsrc name=testtone freq=100 volume=0.0 ! audio/x-raw,format=S16LE,rate=44100,layout=interleaved,channels=2 ! queue ! audioswitch.sink_0 input-selector name=audioswitch ! queue ! audiorate ! audioconvert ! audioresample ! audio/x-raw,format=S16LE,rate=44100,layout=interleaved,channels=2 ! queue ! voaacenc bitrate=128000 ! aacparse ! audio/mpeg,mpegversion=4,stream-format=raw ! flvmux streamable=true name=mux ! queue ! rtmpsink location="rtmp://a.rtmp.youtube.com/live2/x/steve.hvcd-ssyb-esqr-2x2m" sync=true'
global switcher, mainpipe, audioswitcher
mainpipe=Gst.parse_launch(CLI)
switcher= mainpipe.get_by_name("switch")
audioswitcher= mainpipe.get_by_name("audioswitch")
#decoder = mainpipe.get_by_name("decoder1")
#decode.connect("pad-added", self.decoder_callback)
mainpipe.set_state(Gst.State.PLAYING)

try:
	server = ThreadedHTTPServer(('10.2.2.237', 8888), apiHandler) ## this IP address needs to be updated to the internal IP if using on AMazon
	server.serve_forever()
except KeyboardInterrupt:
	server.socket.close()
	sys.exit()


