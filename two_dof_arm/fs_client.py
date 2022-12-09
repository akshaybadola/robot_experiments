import argparse
import base64

import requests
import numpy as np
import cv2 as cv
from common_pyutil.monitor import Timer


timer = Timer()


def show_live(host, port, flip=0, convert=None):
    server = f"http://{host}:{port}"
    while True:
        with timer:
            resp = requests.get(f"{server}/get_frame")
        print(timer.time)
        img = cv.imdecode(np.frombuffer(base64.b64decode(resp.content), dtype=np.uint8),
                          flags=cv.IMREAD_COLOR)
        if convert:
            img = img[:, :, ::-1]
        i = 0
        try:
            cv.imshow("img", img)
            print(i)
            if cv.waitKey(1) == ord('q'):
                cv.destroyAllWindows()
                break
            i += 1
        except KeyboardInterrupt:
            cv.destroyAllWindows()
    cv.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument("--no-bgr2rgb", dest="bgr2rgb", action="store_false")
    args = parser.parse_args()
    show_live(args.host, args.port, convert=args.bgr2rgb)
