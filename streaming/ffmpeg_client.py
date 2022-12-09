import argparse
import time

import cv2 as cv


def main(host, port):
    cap = cv.VideoCapture(f"http://{host}:{port}/stream.m3u8")
    status, img = cap.read()
    i = 0
    try:
        while status:
            cv.imshow("img", img)
            status, img = cap.read()
            print(i)
            if cv.waitKey(1) == ord('q'):
                cv.destroyAllWindows()
                break
            time.sleep(.02)
            i += 1
    except KeyboardInterrupt:
        cap.release()
        cv.destroyAllWindows()
    cap.release()
    cv.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("-p", "--port", type=int, default=8080)
    args = parser.parse_args()
    main(args.host, args.port)
