__author__ = 'Tibbers'

import random, math
import time
from random import randint
import sys, traceback, threading, socket

import subprocess
import os

class ServerWorker:
	SETUP = 'SETUP'
	PLAY = 'PLAY'
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
			seq = str(seq.split('\n')[0])
		except:
			print "I Don't understand the request"
			return;
		# Process SETUP request
		if requestType == self.SETUP:
			if self.state == self.INIT:
				# Update state
				print '-'*60 + "\nSETUP Request Received\n"
				try:
					## self.clientInfo['videoStream'] = VideoStream(filename.split("/")[3])
					self.state = self.READY

				except IOError:
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq)

				self.clientInfo['rtpPort'] = data.split('client_port=')[1].split("-")[0]

				reply = 'RTSP/1.0 200 OK\r\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session']) +'\r\nTransport: RTP/AVP/UDP;unicast;client_port='+str(self.clientInfo['rtpPort'])+';\r\n\r\n'
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

                                # Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp)
				self.clientInfo['worker'].start()

				self.replyRtsp(self.OK_200, seq)
				print '-'*60 + "\nSequence Number ("+ seq + ")\nReplied to client\n" + '-'*60

		elif requestType == self.TEARDOWN:
			print '-'*60 + "\nTEARDOWN Request Received\n" + '-'*60
			self.clientInfo['event'].set()
			self.replyRtsp(self.OK_200, seq)

                elif requestType == self.OPTIONS:
			self.clientInfo['session'] = randint(100000, 999999)
                        print '-'*60 + "\nOPTIONS Request Received\n" + '-'*60
                        reply = "RTSP/1.0 200 OK\r\nCSeq: " + seq + "\nPublic: OPTIONS, DESCRIBE, ANNOUNCE, GET_PARAMETER, RECORD, SET_PARAMETER, SETUP, TEARDOWN, PLAY\r\nServer: Python RTSP server\r\n\r\n"
                        print reply
                        connSocket = self.clientInfo['rtspSocket'][0]
                        connSocket.send(reply)
			print '-'*60 + "\nSequence Number ("+ seq + ")\nReplied to client\n" + '-'*60

                elif requestType == self.DESCRIBE:
                        print '-'*60 + "\nDESCRIBE Request Received\n" + '-'*60
			sdp = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=No Name\r\nc=IN IP4 174.112.184.52\r\nt=0 0\r\na=tool:libavformat 56.40.101\r\nm=video 5000 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\na=fmtp:96 packetization-mode=1\r\n"
                        reply = 'RTSP/1.0 200 OK\r\nCSeq: ' + seq + '\nContent-Type: application/sdp\r\nContent-Length: '+str(len(sdp))+'\r\n\r\n'
                        reply = reply+sdp
                        print reply
                        connSocket = self.clientInfo['rtspSocket'][0]
                        connSocket.send(reply)
                        print '-'*60 + "\nSequence Number ("+ seq + ")\nReplied to client\n" + '-'*60

	def sendRtp(self):
		"""Send RTP packets over UDP."""
		print "sending data to: "+str(self.clientInfo['rtspSocket'][1][0])+":"+str(self.clientInfo['rtpPort'])
		os.chdir('/usr/bin/')
		port = int(self.clientInfo['rtpPort'])
		subprocess.call('ffmpeg -re -i /home/ubuntu/rtsp/videoClip.mov -an -vcodec h264 -f rtp rtp://'+str(self.clientInfo['rtspSocket'][1][0])+':'+str(port), shell=True)
		return

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
