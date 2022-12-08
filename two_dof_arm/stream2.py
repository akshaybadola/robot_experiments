import socket
import time

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput


hostname = "0.0.0.0"
port = 10001

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((hostname, port))
cam = Picamera2()
video_config = cam.create_video_configuration({"size": (1280, 720)})
cam.configure(video_config)
encoder = H264Encoder(1000000)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.listen(0)
cam.encoder = encoder
cam.framerate = 24


# try:
#     conn, addr = sock.accept()
#     stream = conn.makefile("wb")
#     cam.encoder.output = FileOutput(stream)
#     cam.start_encoder()
#     cam.start()
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     cam.stop()
#     conn.close()
#     sock.close()

try:
    conn, addr = sock.accept()
    stream = conn.makefile("wb")
    cam.start_recording(stream, format="h264")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    cam.stop_recording()
    conn.close()
    sock.close()
