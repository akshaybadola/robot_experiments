import argparse
import socket
import time

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput


class Streamer:
    def __init__(self, hostname, port, bit_rate, size, http=False):
        self.hostname = hostname
        self.port = port
        self.cam = Picamera2()
        video_config = self.cam.create_video_configuration({"size": size})
        self.cam.configure(video_config)
        self.size = size
        self.bit_rate = bit_rate
        self.encoder = H264Encoder(bit_rate)
        self.http = http

    def start_tcp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.hostname, self.port))
        self.sock.listen()
        self.cam.encoder = self.encoder
        self.conn, self.addr = self.sock.accept()
        self.stream = self.conn.makefile("wb")
        self.cam.encoder.output = FileOutput(self.stream)
        self.cam.start_encoder()
        self.cam.start()

    def stop_tcp(self):
        self.cam.stop()
        self.conn.close()
        self.sock.close()

    def stop_ffmpeg(self):
        self.cam.stop()

    def start_ffmpeg(self):
        output = FfmpegOutput("-r 25 -f hls -hls_time 4 -hls_list_size 5 -hls_flags delete_segments "
                              "-hls_allow_cache 0 stream.m3u8")
        self.cam.start_recording(self.encoder, output)


def main(method, port, frame_rate, bit_rate, size):
    service = Streamer("0.0.0.0", port)
    try:
        if method == "ffmpeg":
            service.start_ffmpeg()
        elif method == "tcp":
            service.start_tcp()
        else:
            raise ValueError(f"Unknown method {method}")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if method == "ffmpeg":
            service.stop_ffmpeg()
        elif method == "tcp":
            service.stop_tcp()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("method")
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument("-f", "--frame-rate", type=int, default=25)
    parser.add_argument("-b", "--bit-rate", type=int, default=500000)
    parser.add_argument("-s", "--size", default="1280,720")
    args = parser.parse_args()
    size = [*map(int, args.size.split(","))]
    main(args.method, args.port, args.frame_rate, args.bit_rate, size)
