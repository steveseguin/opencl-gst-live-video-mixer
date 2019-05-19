#!/usr/bin/python3

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtsp', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import GObject, Gst, GstRtsp, GstRtspServer
import time

PORT='5554'
MOUNT='/video'

Gst.debug_set_active(True)
Gst.debug_set_default_threshold(3)

if __name__ == "__main__":
    GObject.threads_init()
    loop = GObject.MainLoop()
    Gst.init(None)

    server = GstRtspServer.RTSPServer()
    server.set_service(PORT)

    factory = GstRtspServer.RTSPMediaFactory()
    # factory.set_launch("( v4l2src device=/dev/video0 ! video/x-raw, width=640, height=480, framerate=30/1 ! x264enc ! h264parse ! rtph264pay pt=96 name=pay0 )")
    # factory.set_launch('( videotestsrc is-live=1 ! video/x-raw, width=640, height=480, framerate=30/1 ! x264enc ! flvmux name=mymuxer ! queue ! rtmpsink location="rtmp://a.rtmp.youtube.com/live2/hvcd-ssyb-esqr-2x2m" )')
    factory.set_launch("( videotestsrc is-live=1 ! video/x-raw, width=640, height=480, framerate=30/1 ! x264enc ! rtph264pay name=pay0 pt=96 )")
    factory.set_shared(True)

    pool = GstRtspServer.RTSPAddressPool()
    pool.add_range("224.3.0.0", "224.3.0.10", 5000, 5010, 16)
    factory.set_address_pool(pool)
    factory.set_protocols(GstRtsp.RTSPLowerTrans.UDP)
    server.get_mount_points().add_factory(MOUNT, factory)

    server.attach(None)
    print('running at rtsp://%s:%s%s' % (server.get_address(),  server.get_service(), MOUNT))

    loop.run()

