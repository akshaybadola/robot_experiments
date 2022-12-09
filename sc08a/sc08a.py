from typing import List, Optional
import sys
import time
import argparse

from flask import Flask, request
from werkzeug import serving

import serial


class SC08A:
    """A class to manage SC08A PWM 8 Channel servo controller

    SC08A protocol is via an array of bytes. The number of bytes is determined
    by the command.

    The port when connecting via (linux based) PC and a USB to Serial controller
    (like CP2102) would be :code:`/dev/ttyUSB0``.

    In Raspberry Pi, the serial communication while boot has to be disabled and
    UART has to be enabled. After that the port will appear as :code:`/dev/ttyS0`

    The user should have appropriate write permission on the port.

    Commands `on_motor`, `off_motor` and `get_pos` require a single byte
    Command `set_pos_speed` requires 4 bytes

    For all commands the channels are specified in binary and are OR'ed with
    the first byte

    1. The first byte is the command OR'ed with channels
    2. The concatenation of second and third byte for :meth:`set_pos_speed` determines
       the position
    3. The fourth byte for :meth:`set_pos_speed` determines the speed

    Args:
        portname: The serial port on which the controller is accessible
        baudrate: The baudrate to connect with the serial port
        debug: Whether to print additional debug information


    TODO:
        1. Motor status, is it on or off?

    """

    def __init__(self, portname: str, baudrate: Optional[int], debug: bool = False):
        self.baudrate = baudrate or 9600
        self.debug = debug
        self.port = serial.Serial(portname, self.baudrate, timeout=0.1, write_timeout=0.1)

    def init_all_motors(self):
        """Initialize all motors.

        One has to turn the motor off individually though.

        """
        self.port.write(bytes([0b11000000, 1]))

    def on_motor(self, channels: int):
        """Turn on the motor for the given channel.

        The channels are OR'ed with the first byte

        Args:
            channel: The channels of the servo

        """
        first_byte = 0b11000000 | channels
        self.port.write(bytes([first_byte, 1]))

    def off_motor(self, channels: int):
        """Turn off the motor for the given channel.

        The channels are OR'ed with the first byte

        Args:
            channel: The channel of the servo

        """
        first_byte = 0b11000000 | channels
        self.port.write(bytes([first_byte, 0]))

    def set_pos_speed(self, channels: int, pos: int, speed: int):
        """Set position and speed for the given channels

        The channels are OR'ed with the first byte

        Args:
            channels: The given channels
            pos: Position in TODO range
            speed: speed from 0-255


        """
        byte_1 = 0b11100000 | channels
        str_pos = bin(0b10000000000000 | pos)[3:]
        byte_2 = '0' + str_pos[:7]
        if self.debug:
            print("byte_2", byte_2, int(byte_2, 2))
        byte_2 = int(byte_2, 2)  # type: ignore
        byte_3 = '00' + str_pos[7:]
        if self.debug:
            print("byte_3", byte_3, int(byte_3, 2))
        byte_3 = int(byte_3, 2)  # type: ignore
        byte_4 = speed
        self.port.write(bytes([byte_1, byte_2, byte_3, byte_4]))  # type: ignore

    def get_pos(self, channel: int):
        """Get position of a given channel

        One byte is written, two are read. They are interpreted as int and returned

        Args:
            channel: The channel

        """
        self.port.write(bytes([0b10100000 | channel]))
        high, low = self.port.read(2)
        return int(bin(0b10000000 | high)[3:] + bin(0b1000000 | low)[3:], 2)

    def shutdown(self):
        """Stop the servo controller

        1. Turn off all the motors
        2. Close the serial port

        """
        for i in range(1, 9):
            self.off_motor(i)
        self.port.close()


class Service:
    """Flask service for SCO8A Servo Controller

    Args:
        pins: List of pins to run on the service
        port: The port for the servo controller
        baudrate: Baudrate for the port


    TODO:
        1. Motor status, is it on or off?
        2. Motor running status, is the motor running?
           While running we should not issue new commands to a motor and
           status should be stored internally

    """
    def __init__(self, pins: List[int], port: str, baudrate: Optional[int] = None):
        self.pins = pins
        self.port = port
        self.badurate = baudrate or 9600
        self.app = Flask("Servo")
        self.init_routes()

    def init_controller(self):
        self.controller = SC08A(self.port, self.baudrate)
        self.controller.init_all_motors()

    def init_routes(self):
        @self.app.route("/set_pos", methods=["GET"])
        def _set_pos():
            if "pin" not in request.args:
                return "Pin not given"
            if "pos" not in request.args:
                return "pos (position) not given"
            if "speed" not in request.args:
                print("speed not given. Will use 50")
                speed = 50
            else:
                speed = int(request.args.get("speed"))
            pin = int(request.args.get("pin"))
            pos = int(request.args.get("pos"))
            self.controller.set_pos_speed(pin, pos, speed)
            return f"Setting position for motor: {pin} at: {pos} and speed: {speed}"

        @self.app.route("/get_pos", methods=["GET"])
        def _get_pos():
            if "pin" not in request.args:
                return "Pin not given"
            pin = int(request.args.get("pin"))
            return str(self.controller.get_pos(pin))

        @self.app.route("/reset", methods=["GET"])
        def _reset():
            if "pin" not in request.args:
                return "Pin not given"
            pin = int(request.args.get("pin"))
            self.controller.off_motor(pin)
            return f"Turning motor {pin} OFF"

        @self.app.route("/reset_all", methods=["GET"])
        def _reset_all():
            for pin in self.pins:
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

    def start(self):
        serving.run_simple("0.0.0.0", 2233, self.app, threaded=True)


def test_servo(servo, channel, pos_a=500, pos_b=8000, spd_a=100, spd_b=200):
    """Test a servo motor with an SC08A controller

    The given servo will oscillate between :code:`pos_a,` :code:`pos_b` with
    speeds :code:`spd_a,` :code:`spd_b`

    Args:
        servo: :class:`SC08A` instance
        channel: Servo channel
        pos_a: Position A
        pos_b: Position B
        spd_a: Speed A
        spd_b: Speed B


    """
    while True:
        servo.set_pos_speed(channel, pos_a, spd_a)
        while servo.get_pos(channel) != pos_a:
            time.sleep(.1)
        servo.set_pos_speed(channel, pos_b, spd_b)
        while servo.get_pos(channel) != pos_b:
            time.sleep(.1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--pins", required=True, help="List of comma separated pins")
    parser.add_argument("--port", required=True, help="The serial port")
    parser.add_argument("--baudrate", help="Baudrate for the serial port")
    args = parser.parse_args()
    pins = args.pins.split(",")
    service = Service([*map(int, pins)], args.port, args.baudrate)
    service.start()
