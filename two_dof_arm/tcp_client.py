import socket
import argparse


def recv(sock):
    chunks = []
    bytes_recd = 0
    # bytes_recd < MSGLEN
    while True:
        chunk = sock.recv(2048)
        if chunk == b'':
            return b''.join(chunks)
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    return b''.join(chunks)


def main(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    data = recv(sock)
    with open("test.mp4", "wb") as f:
        f.write(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("hostname")
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument("-f", "--frame-rate", type=int, default=25)
    args = parser.parse_args()
    main(args.hostname, args.port)
