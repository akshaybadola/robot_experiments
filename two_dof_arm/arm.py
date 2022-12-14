from typing import Dict, Optional
import base64
from threading import Thread, Event
from queue import Queue

import cv2 as cv

from flask import Flask, request
from werkzeug import serving
from common_pyutil.monitor import Timer

from sc08a import SC08A


def gstreamer_pipeline(width=1280, height=720, flip_180=False):
    args = ["libcamerasrc", f"video/x-raw, width={width}, height={height}"]
    if flip_180:
        args.append("videoflip method=rotate-180")
    args.append("appsink")
    return (" ! ".join(args))


timer = Timer()


# bufferless VideoCapture
class VideoCapture:
    def __init__(self, pipeline):
        self.cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
        self.q = Queue()
        self.t = Thread(target=self._reader)
        self.t.daemon = True
        self.t.start()

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()   # discard previous (unprocessed) frame
                except Queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        return True, self.q.get()


class TwoDOFArm:
    """A class for controlling Two DOF Robotic Arm with two servo motors and a
    camera at the head. Uses an SC08A controller to control the two motors.

    The camera is captured and images are read on demand via HTTP requests.

    Args:
        width: Image width to capture
        height: Image height to capture
        http_port: HTTP port on which to listen
        pins: A :class:`dict` of pins which designate which motor rotates in the
              horizontal plane and which in the vertical plane
        serial_port: The serial port to which :class:`SC08A` is connected
        baudrate: Optional baudrate of the serial port, defaults to 9600 in :code:`SC08A`

    """
    def __init__(self, width, height, http_port, pins: Dict[str, int], serial_port: str,
                 baudrate: Optional[int] = None):
        self._width = width
        self._height = height
        self._flip = True
        self._gst_pipeline = gstreamer_pipeline(width, height, flip_180=self._flip)
        # self._cap = cv.VideoCapture(self._gst_pipeline, cv.CAP_GSTREAMER)
        self._cap = VideoCapture(self._gst_pipeline)
        self.port = http_port
        self.app = Flask("Frame Server")
        self.pins = pins
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.init_controller()
        self.default_speed = 100
        self.default_increment = 100
        self.app = Flask("Servo")

    def set_capture_properties(self, width, height, flip_180):
        self._width = width
        self._height = height
        self._flip = flip_180
        self._gst_pipeline = gstreamer_pipeline(self._width, self._height, self._flip)
        if self._cap.isOpened():
            self._cap.release()
        self._cap = cv.VideoCapture(self._gst_pipeline, cv.CAP_GSTREAMER)

    def init_controller(self):
        self.controller = SC08A(self.serial_port, self.baudrate)
        self.controller.init_all_motors()

    def start(self):
        self.init_routes()
        serving.run_simple("0.0.0.0", self.port, self.app)

    def _move_horizontal(self, speed, delta=None):
        pin = self.pins["left_right"]
        cur_pos = self.controller.get_pos(pin)
        delta = delta or self.default_increment
        pos = cur_pos + delta
        self.controller.set_pos_speed(pin, pos, speed)
        return f"Setting position for motor: {pin} at: {pos} and speed: {speed}"

    def _move_vertical(self, speed, delta=None):
        pin = self.pins["up_down"]
        cur_pos = self.controller.get_pos(pin)
        delta = delta or self.default_increment
        pos = cur_pos + delta
        self.controller.set_pos_speed(pin, pos, speed)
        return f"Setting position for motor: {pin} at: {pos} and speed: {speed}"

    def _go_left_right(self, lr, speed, delta=None):
        pin = self.pins["left_right"]
        cur_pos = self.controller.get_pos(pin)
        delta = delta or self.default_increment
        if lr == "left":
            pos = cur_pos + delta
        else:
            pos = cur_pos - delta
        self.controller.set_pos_speed(pin, pos, speed)
        return f"Setting position for motor: {pin} at: {pos} and speed: {speed}"

    def _go_up_down(self, ud, speed, delta=None):
        pin = self.pins["up_down"]
        cur_pos = self.controller.get_pos(pin)
        delta = delta or self.default_increment
        if ud == "up":
            pos = cur_pos - delta
        else:
            pos = cur_pos + delta
        self.controller.set_pos_speed(pin, pos, speed)
        return f"Setting position for motor: {pin} at: {pos} and speed: {speed}"

    def init_routes(self):
        def _maybe_get_speed(request):
            if "speed" not in request.args:
                print("speed not given. Will use 50")
                speed = self.default_speed
            else:
                speed = int(request.args.get("speed"))
            return speed

        def _maybe_get_delta(request):
            if "delta" in request.args:
                return int(request.args.get("delta"))
            else:
                return None

        def _get_pin():
            if "pin" not in request.args:
                return "Pin not given"
            pin = int(request.args.get("pin"))
            return pin

        @self.app.route("/set_motion_delta", methods=["GET"])
        def _set_motion_delta():
            if "delta" not in request.args:
                return "Delta not given"
            else:
                delta = int(request.args.get("delta"))
            self.default_increment = delta
            return f"Delta set to {delta}"

        @self.app.route("/set_speed", methods=["GET"])
        def _set_speed():
            if "speed" not in request.args:
                return "Speed not given"
            else:
                speed = int(request.args.get("speed"))
            self.default_speed = speed
            return f"Speed set to {speed}"

        @self.app.route("/set_capture_properties", methods=["GET"])
        def _set_capture_properties():
            width = request.args.get("width")
            height = request.args.get("height")
            flip = request.args.get("flip")
            self.set_capture_properties(width, height, flip)

        @self.app.route("/get_frame", methods=["GET"])
        def __get_frame():
            with timer:
                status, img = self._cap.read()
            # print("read time", timer.time)
            with timer:
                status, buf = cv.imencode(".jpg", img)
            # print("encode time", timer.time)
            data = base64.b64encode(buf)
            return data

        @self.app.route("/horizontal", methods=["GET"])
        def _horizontal():
            speed = _maybe_get_speed(request)
            delta = _maybe_get_delta(request)
            return self._move_horizontal(speed, delta)

        @self.app.route("/vertical", methods=["GET"])
        def _vertical():
            speed = _maybe_get_speed(request)
            delta = _maybe_get_delta(request)
            return self._move_vertical(speed, delta)

        @self.app.route("/go_left", methods=["GET"])
        def _go_left():
            speed = _maybe_get_speed(request)
            delta = _maybe_get_delta(request)
            return self._go_left_right("left", speed, delta)

        @self.app.route("/go_right", methods=["GET"])
        def _go_right():
            speed = _maybe_get_speed(request)
            delta = _maybe_get_delta(request)
            return self._go_left_right("right", speed, delta)

        @self.app.route("/go_up", methods=["GET"])
        def _go_up():
            speed = _maybe_get_speed(request)
            delta = _maybe_get_delta(request)
            return self._go_up_down("up", speed, delta)

        @self.app.route("/go_down", methods=["GET"])
        def _go_down():
            speed = _maybe_get_speed(request)
            delta = _maybe_get_delta(request)
            return self._go_up_down("down", speed, delta)

        @self.app.route("/get_pos", methods=["GET"])
        def _get_pos():
            pin = _get_pin(request)
            return str(self.controller.get_pos(pin))

        @self.app.route("/reset", methods=["GET"])
        def _reset():
            pin = _get_pin(request)
            self.controller.off_motor(pin)
            return f"Turning motor {pin} OFF"

        @self.app.route("/reset_all", methods=["GET"])
        def _reset_all():
            for pin in self.pins.values():
                self.controller.off_motor(pin)
            return "Issued OFF command for all motors"

        @self.app.route("/close", methods=["GET"])
        def _close():
            _reset_all()
            self.controller.shutdown()
            return "Stopped all motors and turned off the controller"

        @self.app.route("/start", methods=["GET"])
        def _start():
            self.init_controller()
            return "Initialized the controller"


if __name__ == '__main__':
    arm = TwoDOFArm(640, 480, 8080, {"left_right": 1, "up_down": 2}, "/dev/ttyUSB0")
    arm.start()
