import time
from threading import Condition, Thread
import base64
import cv2 as cv

from picamera2 import Picamera2

from flask import Flask, request
from werkzeug import serving
from common_pyutil.monitor import Timer

timer = Timer()


class FrameServer:
    def __init__(self, picam2, stream='main', port=8080):
        """A simple class that can serve up frames from one of the Picamera2's configured
        streams to multiple other threads.
        Pass in the Picamera2 object and the name of the stream for which you want
        to serve up frames."""
        self._picam2 = picam2
        self._stream = stream
        self._array = None
        self._condition = Condition()
        self._running = True
        self._count = 0
        self._thread = Thread(target=self._thread_func, daemon=True)
        self.port = port
        self.app = Flask("Frame Server")

    @property
    def count(self):
        """A count of the number of frames received."""
        return self._count

    def start(self):
        """To start the FrameServer, you will also need to start the Picamera2 object."""
        self.init_routes()
        self._thread.start()
        serving.run_simple("0.0.0.0", self.port, self.app)

    def stop(self):
        """To stop the FrameServer, first stop any client threads (that might be
        blocked in wait_for_frame), then call this stop method. Don't stop the
        Picamera2 object until the FrameServer has been stopped."""
        self._running = False
        self._thread.join()

    def _thread_func(self):
        while self._running:
            array = self._picam2.capture_array(self._stream)
            self._count += 1
            with self._condition:
                self._array = array
                self._condition.notify_all()

    def wait_for_frame(self, previous=None):
        """You may optionally pass in the previous frame that you got last time you
        called this function. This will guarantee that you don't get duplicate frames
        returned in the event of spurious wake-ups, and it may even return more
        quickly in the case where a new frame has already arrived."""
        with self._condition:
            if previous is not None and self._array is not previous:
                return self._array
            while True:
                self._condition.wait()
                if self._array is not previous:
                    return self._array

    def init_routes(self):
        @self.app.route("/get_frame", methods=["GET"])
        def __get_frame():
            with timer:
                frame = self.wait_for_frame()
            print(timer.time)
            with timer:
                status, buf = cv.imencode(".jpg", frame)
            print(timer.time)
            data = base64.b64encode(buf)
            return data


if __name__ == '__main__':
    cam = Picamera2()
    server = FrameServer(cam)
    cam.start()
    server.start()
