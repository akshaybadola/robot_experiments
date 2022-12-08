from queue import Queue
from threading import Event
from threading import Thread
import socket
import argparse
import io
from io import BytesIO


import cv2 as cv


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.done = Event()
        self.q = Queue()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print("Connected to socket")

    def recv_2048(self):
        chunks = []
        bytes_recvd = 0
        # bytes_recvd < MSGLEN
        i = 0
        while True and not self.done.is_set():
            chunk = self.sock.recv(2048)
            if chunk == b'':
                return b''.join(chunks)
            chunks.append(chunk)
            bytes_recvd = bytes_recvd + len(chunk)
            i += 1
            if bytes_recvd and bytes_recvd > (256*1024):
                self.q.put(b''.join(chunks))
                chunks = []
                print(i, bytes_recvd)
                bytes_recvd = 0
            if not (i+1) % 100:
                print(i, bytes_recvd)
        self.q.put(b''.join(chunks))

    def recv(self):
        while True and not self.done.is_set():
            chunk = self.sock.recv(2048)
            self.q.put(chunk)

    def start(self):
        t = Thread(target=self.recv)
        t.start()

        try:
            while not self.done.is_set():
                data = self.q.get()
                # print("Writing")
                # with open("test.mp4", "wb") as f:
                #     f.write(data)
                buf = BytesIO(data)
                cap = cv.VideoCapture(buf)
            t.join()
            self.sock.close()
        except KeyboardInterrupt:
            print("Interrupt")
            self.done.set()
            t.join()
            self.sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("hostname")
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument("-f", "--frame-rate", type=int, default=25)
    args = parser.parse_args()
    client = Client(args.hostname, args.port)
    client.start()
