## should support both Python 2.7 and Python 3.5

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
import numpy as np
import cv2  ## not important, but used for loading static images, computer vision effects, and drawing functions.
import binascii
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
import random
import string
try: import md5
except: from hashlib import md5
try: import simplejson as json
except ImportError: import json
import pyopencl as cl ## this will require OpenCL drivers
import io
from PIL import Image
from selenium import webdriver

GObject.threads_init()
Gst.init(None)

Gst.debug_set_active(True)
Gst.debug_set_default_threshold(0)


global buf, background,frame
global stream_srcs, mainpipe, adder, active_shots, ctx, widthout, heightout, fpsout, refresh, queue1, queue2

stream_srcs={}
active_shots = []
mainpipe = None
adder = None
refresh = True

print("Loading OpenCL Device")
platform = cl.get_platforms()
print(platform)
# auto-selecting first OpenCL device. 
my_gpu_devices = platform[0].get_devices(device_type=cl.device_type.GPU)
ctx = cl.Context(devices=my_gpu_devices)

queue1 = cl.CommandQueue(ctx) # opencl related; pipe up and compute?
queue2 = cl.CommandQueue(ctx) # opencl related; pipe down
print("OpenCL Device Loaded")

widthout = 1920  # output resolution.
heightout = 1080
fpsout = 60

class another_input_stream:
	def __init__(self, stream_info):  ## stream id
		global mainpipe, adder
		self.stream_info = stream_info
		if stream_info['src'][:4]=="http":
			self.browser = webdriver.PhantomJS()
			self.browser.get(stream_info['src'])
			img = Image.open(io.BytesIO(data))
			img = np.asarray(img).astype("uint8")
			h,w,d = np.shape(img)
			if w>widthout:
				w=widthout
			if h>heightout:
				h=heightout
			frame = background.copy()
			if d==4:
				alpha = np.repeat(img[0:h,0:w,3], 3).reshape( (h,w,3) ).astype(np.float32) / 255.0
				frame[0:h,0:w,:] = background[0:h,0:w,:]*(1-alpha)+img[0:h,0:w,0:3]*(alpha)
			else:
				frame[0:h,0:w,:] = img[0:h,0:w,:]
			stream_srcs[appsink.get_property("name")]['frame'] = frame
			
		## I'm creating a new pipeline for simplicity
		## attaching it to the mainpipe instead works as well.
		#self.pipeline = Gst.Pipeline.new(self.stream_info['md5'])
		self.pipeline = mainpipe
		decodebin = Gst.ElementFactory.make("uridecodebin")
		self.pipeline.add(decodebin)
		decodebin.connect("pad-added", self.decoder_callback)
		decodebin.set_property('uri', stream_info['src'])
		decodebin.set_state(Gst.State.PLAYING)
        # Creates a bus and set callbacks to receive errors
		self.bus = self.pipeline.get_bus()
		self.bus.add_signal_watch()
		self.bus.connect("message::eos", self.on_eos)
		self.bus.connect("message::error", self.on_error)

	def on_eos(self, bus, msg):
		print("Stop playback on end of stream")
		self.stop()

	def on_error(self, bus, msg):
		print("Print error message and exit on error")
		error = msg.parse_error()[1]
		self.exit(error)

	def on_message(self,bus, message):
		t = message.type
		if t == Gst.MessageType.ERROR:
			error_0 = Gst.Message.parse_error (message)[0]
			error_1 = Gst.Message.parse_error (message)[1]
			print(error_0)
			print(error_1)
		elif t == Gst.MessageType.EOS:
			print ("End of Media")
	
	def decoder_callback(self, decoder, pad):
		global mainpipe, stream_srcs, adder
		#print("NEW PAD ******************************** callback")
		caps = pad.query_caps(None)
		structure_name = caps.to_string()
		if structure_name.startswith("video"):
			caps = str(caps)
			if caps.find("framerate=(fraction)[ 0/1,")  == -1: ## video pad
				try:
					appsink = Gst.ElementFactory.make("appsink")
					appsink.set_property("name",self.stream_info['md5'])
					appsink.set_property("max_buffers",1) ##  only keep most recent frame; dependent on drop. (else will pause stream)
					appsink.set_property("drop",True) ## drop old frames
					appsink.set_property("emit-signals",True)
					appsink.set_property('sync',True) ## playback in real-time (don't jump ahead)
					self.pipeline.add(appsink)
					pad.link(appsink.get_static_pad("sink")) ##
					self.stream_info['status'] = "connected"
					self.stream_info['decoder'] = decoder
					self.stream_info['frame'] = None
					stream_srcs[self.stream_info['md5']] = self.stream_info
					appsink.connect('new-sample', self.on_new_buffer)
					appsink.set_state(Gst.State.PLAYING)
				except:
					print("ERRO WITH DECODER CALLBACK")

			else:
				print("picture")
				## the imagefreeze element can enable us to use PNGs
				## I'd suggest we load PNGs outside of Gstreamer tho; less CPU overhead.
		elif structure_name.startswith("audio"):
			return None
			audiorate = Gst.ElementFactory.make("audiorate")
			audioconvert = Gst.ElementFactory.make("audioconvert")
			audioresample = Gst.ElementFactory.make("audioresample")
			capsfilter = Gst.ElementFactory.make("capsfilter","audio/x-raw,format=S8,rate=44100,channels=1,depth=16,signed=true,endianess=1234,width=16")
			
			self.pipeline.add(audiorate)
			self.pipeline.add(audioconvert)
			self.pipeline.add(audioresample)
			self.pipeline.add(capsfilter)
			
			pad.link(audiorate.get_static_pad("sink")) ##
			audiorate.link_pads('src',audioresample,'sink')
			audioresample.link_pads('src',audioconvert,'sink')
			audioconvert.link_pads('src',capsfilter,'sink')
			capsrc = capsfilter.get_static_pad("src")
			addsink = adder.get_request_pad("sink_%u")	
			capsrc.link(addsink)
			
			#decoder.set_state(Gst.State.PLAYING)
			#pad.set_offset(mainpipe.query_position(Gst.Format.TIME)[1])
			#decoder.sync_state_with_parent()

		else:
			print("Unknown structure")
		return None	
		## these commands are useful if we're only using a single pipeline; syncing functions
		#pad.set_offset(mainpipe.query_position(Gst.Format.TIME)[1])
		#decoder.sync_state_with_parent()

	def on_new_buffer(self, appsink):
		global stream_srcs,ctx,widthout, heightout, fpsout, refresh
		try:
			sample = appsink.emit('pull-sample')
			buf=sample.get_buffer()
			if (buf.get_size()<100):
				print("buffer size too small")
				return False
			data=buf.extract_dup(0,buf.get_size())
			input = np.frombuffer(data, np.uint8)
			stream_srcs[appsink.get_property("name")]['frame'] = input
			stream_srcs[appsink.get_property("name")]['used'] = False
		except:
			print("on new buffer FAIL - 1")
			return False
		if ((stream_srcs[appsink.get_property("name")]['status']=="connected") | (stream_srcs[appsink.get_property("name")]['status']=="updating")):
			try:
				print("******************* ON NEW BUFFER -- FIRST PASS")
				caps = sample.get_caps()
			
				stream_srcs[appsink.get_property("name")]['format'] = caps.get_structure(0).get_value('format')
				stream_srcs[appsink.get_property("name")]['height'] = caps.get_structure(0).get_value('height')
				stream_srcs[appsink.get_property("name")]['width'] =  caps.get_structure(0).get_value('width')
			
				format = caps.get_structure(0).get_value('format')
				width = caps.get_structure(0).get_value('width')
				height = caps.get_structure(0).get_value('height')
			
				print(width,height,format)
				x = stream_srcs[appsink.get_property("name")]['x']
				y = stream_srcs[appsink.get_property("name")]['y']
				w = stream_srcs[appsink.get_property("name")]['w']
				h = stream_srcs[appsink.get_property("name")]['h']
				if w == -1:
					w = width
					sx = 1
				else:
					sx = 1.0*w/width
				if h == -1:
					h = height
					sy = 1
				else:
					sy = 1.0*h/height
			except:
				print("on new buffer FAIL - 2")
				return False
			## In this currently version, I'm only supporting YUV420 input.
			if format == "I420": ## http://www.equasys.de/colorconversion.html
				try:
					# OpenCL kernel code
					interpolate=""
					if ((sx>1.0) | (sy>1.0)): ## supports scaling up to 200%, after that it breaks down -- just a short term implementation.
						interpolate+="""
						frame_gpu[(i0+1)*3+2] = m0;	
						frame_gpu[(i0+1)*3+1] = k0;	
						frame_gpu[(i0+1)*3] = j0; 
						
						frame_gpu[(i0+"""+str(widthout)+""")*3+2] = m0; 
						frame_gpu[(i0+"""+str(widthout)+""")*3+1] = k0; 
						frame_gpu[(i0+"""+str(widthout)+""")*3] = j0; 
						
						frame_gpu[((i0+"""+str(widthout)+""")+1)*3+2] = m0; 
						frame_gpu[((i0+"""+str(widthout)+""")+1)*3+1] = k0; 
						frame_gpu[((i-1+"""+str(widthout)+""")+1)*3] = j0; 
						"""
					skipx=""
					if w+x>widthout:
						skipx+="""
						if (x0>="""+str((widthout-x-1)/sx )+"""){
							return;
						}
						"""
					skipy=""
					if y+h>heightout:
						skipy+="""
						if (y0>="""+str(int((heightout-y)/sy))+"""){
							return;
						}
						"""
						
					code = """
					__kernel void app(__global uchar* a, __global uchar* frame_gpu) {
						int i = get_global_id(0);
						
						int x0 = i%"""+str(width)+""";
						"""+skipx+"""
						int y0 = i/"""+str(width)+""";
						"""+skipy+"""
						
						int m = x0/2 + (y0/2)*"""+str(int(width/2))+""";
						int k =  m + """+str(width)+"""*"""+str(height)+""";
						int j =  m + """+str(width)+"""*"""+str(height)+"""*1.25;
						
						int i0 = (int)(y0*"""+str(sy)+""")*"""+str(widthout)+"""+ x0*"""+str(sx)+"""+"""+str(x+y*widthout)+""";
						
						int m0 = a[i] + 1.4 * a[j] - 179.2;
						int k0 = a[i] - 0.343 *  a[k] - 0.711 *  a[j] + 134.912;
						int j0 = a[i] + 1.765 *  a[k] - 225.92;
						
						frame_gpu[i0*3+2] = m0;
						frame_gpu[i0*3+1] = k0;
						frame_gpu[i0*3]   = j0;
						
						"""+interpolate+"""
					}
					"""
				except:
					print("on new buffer FAIL - 3")
					return False
				try:
					i420 = cl.Program(ctx, code).build()
					stream_srcs[appsink.get_property("name")]['filter']=i420
				except:
					print("on new buffer FAIL - 4")
					print("Couldn't build kernel")
					return False
				refresh = True
				print("loaded filter set")
				stream_srcs[appsink.get_property("name")]['status']="ready"
			else:
				print("unsupported color format")
		return False
		
	## useful for disconnecting live streams on a shared pipeline. 
	## ignore for now
def gen_cb(a, b, *c):
	return Gst.PadProbeReturn.OK	
	
def create_entry(o):
	global stream_srcs
	try:
		m = md5()
	except:
		m = md5.new()
	m.update(o['src'].encode('utf-8'))
	m = m.hexdigest()
	print("incoming", o['src'])
	if m not in stream_srcs:
		stream_info = {}
		stream_info['md5'] = m
		stream_info['src'] = o['src']
		stream_info['decoder'] = None
		stream_info['status'] = "pending"
		stream_srcs[m] = stream_info
		thread.start_new_thread( another_input_stream, (stream_info, ))
	elif (stream_srcs[m]['status'] == "connected"):
		stream_info = stream_srcs[m]
	elif (stream_srcs[m]['status'] != "pending"):
		stream_info = stream_srcs[m]
		if (stream_srcs[m]['action'] == "preload"): ## MAKE SURE the preloaded SHOT TYPE has the same shot type as what you are going LIVE with. else it might have an issue
			stream_info['status'] = "updating"
		print("Already ready ; updating", o['src'])
	else:
		stream_info = stream_srcs[m]
		print("Not yet ready; updating. Warning: Rapid succession in changes may lead to delayed or failed updated", o['src'])

	if ("action" in o):
		stream_info['action'] = o['action']
	else:
		stream_info['action'] = "preload"

	if ("x" in o):
		stream_info['x'] = int(o['x'])
	else:
		stream_info['x'] = 0
	if ("y" in o):
		stream_info['y'] = int(o['y'])
	else:
		stream_info['y'] = 0
	if ("w" in o):
		stream_info['w'] = int(o['w'])
	else:
		stream_info['w'] = -1
	if ("h" in o):
		stream_info['h'] = int(o['h'])
	else:
		stream_info['h'] = -1
	if ("z" in o):
		stream_info['z'] = int(o['z'])
	else:
		stream_info['z'] = 0
			
class apiHandler(BaseHTTPRequestHandler):  ## a basic webserver.
	def do_HEAD(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
	def do_GET(self): ## useful for single-stream shot updates
		o = parse.urlparse(self.path)
		o = dict(parse.parse_qsl(o.query))
		if ("src" in o):
			create_entry(o)
			self.send_response(200)
			self.send_header('Content-type','text/html')
			self.send_header('Access-Control-Allow-Origin','*')
			self.end_headers()
			#self.wfile.write(m)
			return
		else:
			self.send_response(200)
			self.send_header('Content-type','text/html')
			self.send_header('Access-Control-Allow-Origin','*')
			self.end_headers()
			for i in stream_srcs:
				print("- "+str(i)+" -")
				print(stream_srcs[i]['status'],stream_srcs[i]['action'])
				out = stream_srcs[i]['decoder'].get_state(9999999)
				print(out)
			print("unknown HTTP request inbound")
			return
	def do_POST(self):  ## useful for complete multi-shot definitions
			self.data_string = self.rfile.read(int(self.headers['Content-Length'])).decode('utf8')
			data = json.loads(self.data_string)

			self.send_response(200)
			self.send_header('Access-Control-Allow-Origin','*')
			self.end_headers()
			for i in range(len(data)):
				print(data[i])
				create_entry(data[i])
			
			return
	def do_OPTIONS(self):
			self.send_response(200)
			self.send_header('Access-Control-Allow-Headers','Origin, X-Requested-With, Content-Type, Accept')
			self.send_header('Access-Control-Allow-Origin','*')
			self.end_headers()
			return

def need_new_buffer(appsrc, need_bytes): ## ideally this should fire 30 or 60 times a second typically
	#millis = int(round(time.time() * 1000))
	global stream_srcs, adder, mainpipe, widthout, heightout, fpsout, refresh, buf, background, frame, frame_gpu, ctx, queue1, queue2#, avg
	while need_bytes>0:
		try:
			streamCount = len(stream_srcs)
			if refresh==True: ## if background needs to be updated.  This way opens itself to some occiassional bugging
				refresh = False
				print("ACTIVE SHOTS UPDATED")
				frame = background.copy() ## frame is the output and reference size
				frame_gpu = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=np.ravel(frame)) ## If we want a background imagei
				#frame_gpu = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, frame.nbytes) ## No background image; slightly faster
			if streamCount > 0:
				for i in stream_srcs:
					if (((stream_srcs[i]['status']=="ready") | (stream_srcs[i]['status']=="updating")) & (stream_srcs[i]['action'] == "live" )):
						try:
							height = stream_srcs[i]['height']
							width = stream_srcs[i]['width']
							input_dev = cl.Buffer(ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=np.ravel(stream_srcs[i]['frame']))
							event = stream_srcs[i]['filter'].app(queue1, np.ravel(stream_srcs[i]['frame'][0:height*width]).shape, None, input_dev, frame_gpu)
							event.wait()
						except Exception as e:
							if (streamCount == len(stream_srcs)):
								print("Video dropped due to error")
								stream_srcs[i]['status']="error"
							print("frame rendering failed; skipping frame",i)
							print(e)
				
				cl.enqueue_copy(queue2, frame, frame_gpu) ## pull final frame from GPU
			############
			buf.fill(0,frame.tostring())
			appsrc.emit("push-buffer", buf)
			need_bytes-=frame.nbytes
		except Exception as e: 
			print(str(e))
			print("ERRRRRRRRRRRRRROR")
			time.sleep(0.03)
			
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	pass

#CLI = 'appsrc name=mysource format=TIME do-timestamp=TRUE min-percent=50 max-bytes=1000000000  is-live=TRUE caps="video/x-raw,interlace-mode=progressive,format=BGR,width='+str(widthout)+',height='+str(heightout)+',framerate=(fraction)'+str(fpsout)+'/1,pixel-aspect-ratio=(fraction)1/1" ! queue ! videoconvert ! fakesink'

CLI = 'appsrc name=mysource format=TIME do-timestamp=TRUE is-live=TRUE min-percent=50 max-bytes=1000000000 caps="video/x-raw,interlace-mode=progressive,format=BGR,width='+str(widthout)+',height='+str(heightout)+',framerate=(fraction)'+str(fpsout)+'/1,pixel-aspect-ratio=(fraction)1/1" ! timeoverlay halignment=right valignment=bottom text="Stream time:" shaded-background=true font-desc="Sans, 32" ! videoconvert ! videoscale ! videorate ! queue ! capsfilter caps="video/x-raw,format=I420,width='+str(widthout)+',height='+str(heightout)+',framerate=(fraction)30/1" ! queue ! x264enc cabac=false aud=true tune=zerolatency byte-stream=false sliced-threads=true threads=4 speed-preset=1 bitrate=2000 key-int-max=20 bframes=0 ! queue ! h264parse ! queue ! video/x-h264,profile=main ! queue ! mux. audiotestsrc name=testtone freq=100 volume=0.0 ! audio/x-raw,format=S8,rate=44100,channels=1,depth=16,signed=true,endianess=1234,width=16 ! audiorate ! audioconvert ! audioresample ! adder name=audioadder is-live=true  ! audioconvert ! audioresample ! queue ! voaacenc bitrate=128000 ! aacparse ! audio/mpeg,mpegversion=4,stream-format=raw ! flvmux streamable=true name=mux ! rtmpsink location="rtmp://a.rtmp.youtube.com/live2/x/steve.hvcd-ssyb-esqr-2x2m" sync=false'

def message_handler( bus, message):
        struct = message.get_structure()
        if message.type == Gst.MessageType.EOS:
                ## delete appsink from stream list
                print('Stream ended.')

mainpipe=Gst.parse_launch(CLI)
appsrc= mainpipe.get_by_name("mysource")
adder = mainpipe.get_by_name("audioadder")
url = "http://stevesserver.com/0uueOOL.jpg"
resp = urlopen(url)
background = np.zeros((widthout,heightout,3)).astype("uint8") 
background = np.asarray(bytearray(resp.read()), dtype="uint8")
background = cv2.imdecode(background, cv2.IMREAD_COLOR)  ## this is the part that needs OpenCV . 
background = cv2.resize(background, (widthout, heightout)) ## remove it if you don't want a background image

frame = background.copy()
buf = Gst.Buffer.new_allocate(None, len(frame.tostring()), None)

appsrc.connect('need-data', need_new_buffer)
mainpipe.set_state(Gst.State.PLAYING)

try:
	server = ThreadedHTTPServer(('10.2.2.237', 8888), apiHandler) ## this IP address needs to be updated to the internal IP if using on AMazon
	server.serve_forever()
except KeyboardInterrupt:
	server.socket.close()
	sys.exit()


