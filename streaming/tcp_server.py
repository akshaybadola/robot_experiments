import argparse
import socket
import time

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput



def main(port, frame_rate, bit_rate, size):
    hostname = "0.0.0.0"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((hostname, port))
    cam = Picamera2()
    video_config = cam.create_video_configuration({"size": size})
    cam.configure(video_config)
    encoder = H264Encoder(bit_rate)
    sock.listen(0)
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
        output = FileOutput(stream)
        cam.start_recording(encoder, stream)
        # server only 1 second
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cam.stop_recording()
        conn.close()
        sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("method")
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument("-f", "--frame-rate", type=int, default=25)
    parser.add_argument("-b", "--bit-rate", type=int, default=500000)
    parser.add_argument("-s", "--size", default="1280,720")
    args = parser.parse_args()
    size = [*map(int, args.size.split(","))]
    main(args.port, args.frame_rate, args.bit_rate, size)
