import base64
import cv2 as cv

from flask import Flask
from werkzeug import serving
from common_pyutil.monitor import Timer


def gstreamer_pipeline(width=1280, height=720, flip_180=False):
    args = ["libcamerasrc", f"video/x-raw, width={width}, height={height}"]
    if flip_180:
        args.append("videoflip method=rotate-180")
    args.append("appsink")
    return (" ! ".join(args))


timer = Timer()


class FrameServer:
    def __init__(self, width, height, port=8080):
        self._gst_pipeline = gstreamer_pipeline(width, height, flip_180=True)
        self._cap = cv.VideoCapture(self._gst_pipeline, cv.CAP_GSTREAMER)
        self.port = port
        self.app = Flask("Frame Server")

    def start(self):
        self.init_routes()
        serving.run_simple("0.0.0.0", self.port, self.app)

    def init_routes(self):
        @self.app.route("/get_frame", methods=["GET"])
        def __get_frame():
            with timer:
                status, img = self._cap.read()
            print("read time", timer.time)
            with timer:
                status, buf = cv.imencode(".jpg", img)
            print("encode time", timer.time)
            data = base64.b64encode(buf)
            return data


if __name__ == '__main__':
    server = FrameServer(640, 480)
    server.start()
