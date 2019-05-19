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
import subprocess

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
	#browser = webdriver.Firefox()
	# PhantomJS supports Background Transparencies, but slow
	browser.set_window_size(1280, 720)

print("browser loaded")

#browser.get('https://streampro.io/overlay/58dc422a3800a1324238f9d0/XVGj8p5rjDuL1y3fiFH92j7yU9daJutC')
browser.get('https://streampro.io/overlay/58dc422a3800a1324238f9d0/XVGj8p5rjDuL1y3fiFH92j7yU9daJutC')
print("browser heading to website")

cmdstring = ('ffmpeg', 
    '-y',
    '-f', 'image2pipe',
    '-re',
    '-framerate', '1', 
    '-i', '-', # tell ffmpeg to expect raw video from the pipe
    '-fflags','nobuffer',
    '-vcodec', 'libvpx',
    '-g', '1',
#    '-crf','4', '-b:v','10M',
    '-vsync','0',
#    '-g', '15',
 #   '-cpu-used', '0',
    '-muxdelay','5',
    '-pix_fmt', 'yuva420p',
    '-quality', 'realtime',
    '-framerate', '1',
    '-deadline','realtime',
    '-f','rtsp',
    'rtsp://alpha-wowza1.stageten.tv:1935/stageten/stream-GdBEA1kzr620-i9x23LZUGc') # output encoding

p = subprocess.Popen(cmdstring, stdin=subprocess.PIPE)

for frame in range(10000):
	browser.execute_script("document.getElementsByTagName('body')[0].style.maxWidth = '1280px';")
	data = browser.get_screenshot_as_png()
	p.stdin.write(data)
        #buf = Gst.Buffer.new_allocate(None, len(data), None)
        #buf.fill(0,data)
        #appsrc.emit("push-buffer", buf)
	
        #browser.execute_script("document.getElementsByTagName('body')[0].style.maxWidth = '1280px';")

p.communicate()
