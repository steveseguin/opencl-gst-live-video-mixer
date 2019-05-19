__author__ = 'Tibbers'

import random, math
import time
from random import randint
import sys, traceback, threading, socket

import subprocess
import os

from VideoStream import VideoStream
from RtpPacket import RtpPacket

class ServerWorker:
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'
	OPTIONS = 'OPTIONS'
	DESCRIBE = 'DESCRIBE'

	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	OK_200 = 0
	FILE_NOT_FOUND_404 = 1
	CON_ERR_500 = 2

	clientInfo = {}

	def __init__(self, clientInfo):
		self.clientInfo = clientInfo

	def run(self):
		threading.Thread(target=self.recvRtspRequest).start()

	def recvRtspRequest(self):
		"""Receive RTSP request from the client."""
		connSocket = self.clientInfo['rtspSocket'][0]
		while True:
			data = connSocket.recv(4096)  ###
			if data:
				print '-'*60 + "\nData received:\n" + '-'*60
				print data
				self.processRtspRequest(data)

	def processRtspRequest(self, data):
		"""Process RTSP request sent from the client."""
		# Get the request type
		try:
			request = data.split('\n')
			line1 = request[0].split(' ')
			requestType = line1[0]
			# Get the media file name
			filename = line1[1]
			# Get the RTSP sequence number
			seq = data.split('CSeq: ')[1]
			print seq
			seq = str(seq.split('\n')[0])
			print seq
		except:
			print "I Don't understand the request"
			return;
		# Process SETUP request
		if requestType == self.SETUP:
			if self.state == self.INIT:
				# Update state
				print '-'*60 + "\nSETUP Request Received\n"
				try:
					self.clientInfo['videoStream'] = VideoStream(filename.split("/")[3])
					self.state = self.READY

				except IOError:
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq)

				# Generate a randomized RTSP session ID
				#self.clientInfo['session'] = randint(100000, 999999)
				self.clientInfo['rtpPort'] = data.split('client_port=')[1].split("-")[0]
				

				reply = 'RTSP/1.0 200 OK\r\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session']) +'\r\nTransport: RTP/AVP/UDP;unicast;client_port='+str(self.clientInfo['rtpPort'])+';\r\n\r\n'
				print "******************************************************************"
        	                print reply
	                        connSocket = self.clientInfo['rtspSocket'][0]
                	        connSocket.send(reply)

				print "sequenceNum is " + seq
				# Get the RTP/UDP port from the last line
				print '-'*60 + "\nrtpPort is: " + str(self.clientInfo['rtpPort']) + "\n" + '-'*60
				print "filename is " + filename + " ... " + filename.split("/")[3]

		# Process PLAY request
		elif requestType == self.PLAY:
			print "PLAY STATE"
			if self.state == self.READY:
				print '-'*60 + "\nPLAY Request Received\n" + '-'*60
				self.state = self.PLAYING

				# Create a new socket for RTP/UDP
				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

				self.replyRtsp(self.OK_200, seq)
				print '-'*60 + "\nSequence Number ("+ seq + ")\nReplied to client\n" + '-'*60

				# Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp)
				self.clientInfo['worker'].start()
		# Process RESUME request
			elif self.state == self.PAUSE:
				print '-'*60 + "\nRESUME Request Received\n" + '-'*60
				self.state = self.PLAYING

		# Process PAUSE request
		elif requestType == self.PAUSE:
			if self.state == self.PLAYING:
				print '-'*60 + "\nPAUSE Request Received\n" + '-'*60
				self.state = self.READY

				self.clientInfo['event'].set()

				self.replyRtsp(self.OK_200, seq)

		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			print '-'*60 + "\nTEARDOWN Request Received\n" + '-'*60
			self.clientInfo['event'].set()
			self.replyRtsp(self.OK_200, seq)
			# Close the RTP socket
			self.clientInfo['rtpSocket'].close()

                elif requestType == self.OPTIONS:
			self.clientInfo['session'] = randint(100000, 999999)
                        print '-'*60 + "\nOPTIONS Request Received\n" + '-'*60
                        reply = "RTSP/1.0 200 OK\r\nCSeq: " + seq + "\nPublic: OPTIONS, DESCRIBE, ANNOUNCE, GET_PARAMETER, RECORD, SET_PARAMETER, SETUP, TEARDOWN, PLAY, PAUSE\r\nServer: Python RTSP server\r\n\r\n"
                        print reply
                        connSocket = self.clientInfo['rtspSocket'][0]
                        connSocket.send(reply)
			print '-'*60 + "\nSequence Number ("+ seq + ")\nReplied to client\n" + '-'*60

                elif requestType == self.DESCRIBE:
                        print '-'*60 + "\nDESCRIBE Request Received\n" + '-'*60

			#sdp = "v=0\r\no=- 3047637804676463751 1 IN IP4 10.2.2.237\r\ns=Session streamed with GStreamer\r\ni=rtsp-server\r\nt=0 0\r\na=tool:GStreamer\r\na=type:broadcast\r\na=control:*\r\na=range:npt=now\r\n-m=video 0 RTP/AVP 96\r\nc=IN IP4 0.0.0.0"
			sdp = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=No Name\r\nc=IN IP4 174.112.184.52\r\nt=0 0\r\na=tool:libavformat 56.40.101\r\nm=video 5000 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\na=fmtp:96 packetization-mode=1\r\n"
                        #sdp = "v=0\r\nm=video 5000 RTP/AVP 96\r\nc=IN IP4 127.0.0.1\r\na=rtpmap:96 H264/90000\r\n"
                        reply = 'RTSP/1.0 200 OK\r\nCSeq: ' + seq + '\nContent-Type: application/sdp\r\nContent-Length: '+str(len(sdp))+'\r\n\r\n'
                        reply = reply+sdp
                        print reply
                        connSocket = self.clientInfo['rtspSocket'][0]
                        connSocket.send(reply)
                        print '-'*60 + "\nSequence Number ("+ seq + ")\nReplied to client\n" + '-'*60

	def sendRtp(self):
		"""Send RTP packets over UDP."""

		counter = 0
		threshold = 10
		print "sending data to: "+str(self.clientInfo['rtspSocket'][1][0])+":"+str(self.clientInfo['rtpPort'])
		os.chdir('/usr/bin/')
		port = int(self.clientInfo['rtpPort'])
		subprocess.call('ffmpeg -re -i /home/ubuntu/rtsp/videoClip.mov -an -vcodec h264 -f rtp rtp://'+str(self.clientInfo['rtspSocket'][1][0])+':'+str(port), shell=True)
		return

		while True:
			jit = math.floor(random.uniform(-13,5.99))
			jit = jit / 1000

			self.clientInfo['event'].wait(0.05 + jit)
			jit = jit + 0.020

			# Stop sending if request is PAUSE or TEARDOWN
			if self.clientInfo['event'].isSet():
				break

			data = self.clientInfo['videoStream'].nextFrame()
			#print '-'*60 + "\ndata from nextFrame():\n" + data + "\n"
			if data:
				frameNumber = self.clientInfo['videoStream'].frameNbr()
				try:
					#address = 127.0.0.1 #self.clientInfo['rtspSocket'][0][0]
					#port = '25000' #int(self.clientInfo['rtpPort'])

					#print '-'*60 + "\nmakeRtp:\n" + self.makeRtp(data,frameNumber)
					#print '-'*60

					#address = self.clientInfo['rtspSocket'][1]   #!!!! this is a tuple object ("address" , "")
					port = int(self.clientInfo['rtpPort'])
#					os.chdir('/usr/bin/')
#					subprocess.call('ffmpeg -re -f lavfi -i aevalsrc="sin(400*2*PI*t)" -ar 8000 -f mulaw -f rtp rtp://174.112.184.52:'+str(port), shell=True)

					prb = math.floor(random.uniform(1,100))
					if prb > 5.0:
						self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber),(self.clientInfo['rtspSocket'][1][0],port))
						counter += 1
						time.sleep(jit)
				except:
					print "Connection Error"
					print '-'*60
					traceback.print_exc(file=sys.stdout)
					print '-'*60

	def makeRtp(self, payload, frameNbr):
		"""RTP-packetize the video data."""
		version = 2
		padding = 0
		extension = 0
		cc = 0
		marker = 0
		pt = 26 # MJPEG type
		seqnum = frameNbr
		ssrc = 0

		rtpPacket = RtpPacket()

		rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)

		return rtpPacket.getPacket()

	def replyRtsp(self, code, seq):
		"""Send RTSP reply to the client."""
		if code == self.OK_200:
			#print "200 OK"
			reply = 'RTSP/1.0 200 OK\r\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session']) +'\r\n\r\n'
			print reply
			connSocket = self.clientInfo['rtspSocket'][0]
			connSocket.send(reply)
		elif code == self.FILE_NOT_FOUND_404:
			print "404 NOT FOUND"
		elif code == self.CON_ERR_500:
			print "500 CONNECTION ERROR"
