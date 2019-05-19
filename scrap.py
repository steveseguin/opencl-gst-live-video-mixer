import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
import io
from PIL import Image
GObject.threads_init()
Gst.init(None)
Gst.debug_set_active(True)
Gst.debug_set_default_threshold(0)

from pyvirtualdisplay import Display
#from pyvirtualdisplay.smartdisplay import SmartDisplay
from selenium import webdriver
import numpy as np
import cv2
try: from urllib.request import urlopen
except: from urllib import urlopen
try: input = raw_input
except NameError: pass
import time
global widthout, heightout, fpsout, browser
widthout = 1280
heightout = 720
fpsout = 30

print("starting")
#global dis

chromeheadless = False

try:
	display = Display(visible=0, size=(widthout, heightout)) ## this isn't needed if using PhantomJS or headless chrome
	display.start()
except:
	print("using windows?")

if chromeheadless == True:
	from selenium.webdriver.chrome.options import Options
	l_option = Options()
	l_option.add_argument('headless')
	l_option.add_argument('disable-notifications')
	l_option.add_argument('disable-extensions')
	l_option.add_argument('window-size=1280,720')
	l_option.add_argument('incognito')
	#l_option.binary_location = '/home/fi11222/Headless_Chromium/headless_shell'
	browser = webdriver.Chrome(chrome_options=l_option)
else:
	browser = webdriver.PhantomJS() # Chrome() / Firefox()
	## PhantomJS supports Background Transparencies, but slow
	browser.set_window_size(1280, 720)

print("browser loaded")

browser.get('https://streampro.io/overlay/58dc422a3800a1324238f9d0/XVGj8p5rjDuL1y3fiFH92j7yU9daJutC')
print("browser heading to website")
global buf, urls
urls = None
def need_new_buffer(appsrc, bytes_needed):
	global buf, widthout, heightout, browser, urls, background
	while True:
		try:
			if urls != None:
				browser.get(urls)
				urls = None
			if chromeheadless == False:
				browser.execute_script("document.getElementsByTagName('body')[0].style.maxWidth = '1280px';")
			data = browser.get_screenshot_as_png()
			img = Image.open(io.BytesIO(data))
			img = np.asarray(img).astype("uint8")
			h,w,d = np.shape(img)
			#print(h,w,d)
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
			buf.fill(0,frame.tostring())
			appsrc.emit("push-buffer", buf)
			return False
		except Exception as e:
			print("ERRORR")
			print(str(e))
			time.sleep(1)



#browser.quit()
#display.stop()
CLI = 'appsrc name=mysource format=TIME do-timestamp=TRUE is-live=TRUE min-percent=50 max-bytes=1000000000 caps="video/x-raw,interlace-mode=progressive,format=RGB,width='+str(widthout)+',height='+str(heightout)+',framerate=(fraction)'+str(fpsout)+'/1,pixel-aspect-ratio=(fraction)1/1" ! timeoverlay halignment=right valignment=bottom text="Stream time:" shaded-background=true font-desc="Sans, 32" ! videoconvert ! videoscale ! videorate ! queue ! capsfilter caps="video/x-raw,format=I420,width='+str(widthout)+',height='+str(heightout)+',framerate=(fraction)30/1" ! queue ! x264enc cabac=false aud=true tune=zerolatency byte-stream=false sliced-threads=true threads=4 speed-preset=1 bitrate=2000 key-int-max=20 bframes=0 ! queue ! h264parse ! queue ! video/x-h264,profile=main ! queue ! mux. audiotestsrc name=testtone freq=100 volume=0.0 ! audio/x-raw,format=S8,rate=44100,channels=1,depth=16,signed=true,endianess=1234,width=16 ! audiorate ! audioconvert ! queue ! voaacenc bitrate=128000 ! aacparse ! audio/mpeg,mpegversion=4,stream-format=raw ! flvmux streamable=true name=mux ! rtmpsink location="rtmp://a.rtmp.youtube.com/live2/x/steve.hvcd-ssyb-esqr-2x2m" sync=false'

mainpipe=Gst.parse_launch(CLI)
appsrc= mainpipe.get_by_name("mysource")
appsrc.set_property("emit-signals",True)

url = "http://stevesserver.com/0uueOOL.jpg"
resp = urlopen(url)
background = np.zeros((widthout,heightout,3)).astype("uint8")
background = np.asarray(bytearray(resp.read()), dtype="uint8")
background = cv2.imdecode(background, cv2.IMREAD_COLOR)  ## this is the part that needs OpenCV .
background = cv2.resize(background, (widthout, heightout)) ## remove it if you don't want a background image
buf = Gst.Buffer.new_allocate(None, len(background.tostring()), None)

appsrc.connect('need-data', need_new_buffer)
mainpipe.set_state(Gst.State.PLAYING)

buf.fill(0, background.tostring())
appsrc.emit("push-buffer", buf)

print("End")

while(True):
	urls = input("url: ")
