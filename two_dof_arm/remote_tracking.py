from typing import List, Union
import argparse
import base64

import requests
import numpy as np
import cv2 as cv

from common_pyutil.monitor import Timer
from object_tracking import (get_contours_and_mask_hsv, get_midpoints,
                             draw_bounding_rect_for_contour)


timer = Timer()


class RemoteClient:
    """A client for a remote Two DOF Robotic Arm to capture images and move
    manually with a keyboard and automatically based on deltas of center of
    object from the center of the image.

    Args:
        host: Remote host ip address
        port: Remote port
        img_size: The size of the image [width, height] that we'll receive
        flip: Flip the image?
        convert: Convert from BGR2RGB
        low_val: Low threshold per channel for image
        high_val: High threshold per channel for image

    The current version tracks a red object after converting the image to HSV
    which is fairly easy. A more advanced client should detect specific objects
    and track/record them.

    """

    def __init__(self, host: str, port: Union[int, str],
                 img_size: List[int] = [640, 480], flip: int = 0,
                 convert: bool = False, low_val: List[int] = [0, 0, 0],
                 high_val: List[int] = [255, 255, 255]):
        self._host = host
        self._port = port
        self._flip = flip
        self._convert = convert
        self._server = f"http://{self._host}:{self._port}"
        self._low_val = np.array(low_val)
        self._high_val = np.array(high_val)
        self._img_size = img_size
        self._center = np.array(self._img_size)/2

    def simple_agent(self):
        """A Simple Agent which navigates the robotic arm based on deltas from
        the center of the image.

        """
        server = self._server
        while True:
            key = cv.waitKey(1)
            with timer:
                resp = requests.get(f"{server}/get_frame")
            img = cv.imdecode(np.frombuffer(base64.b64decode(resp.content), dtype=np.uint8),
                              flags=cv.IMREAD_COLOR)
            x_mid = y_mid = x_d = y_d = 0
            try:
                contours, mask = get_contours_and_mask_hsv(img, self._low_val, self._high_val)
                img = np.hstack([img, np.repeat(mask, 3).reshape(*mask.shape, 3)])
                if not len(contours):
                    print("No contour found")
                else:
                    areas = [cv.contourArea(x) for x in contours]
                    sorted_inds = np.argsort(areas)
                    max_area_contour = contours[sorted_inds[-1]]
                    x_mid, y_mid = get_midpoints(max_area_contour)
                    cv.circle(img, (x_mid, y_mid), 10, (0, 255, 0))
                    x_d, y_d = self._center/2
                    print(x_mid, y_mid, x_d, y_d)
                if np.abs(x_d) > 5:
                    resp = requests.get(f"{server}/horizontal?delta={int(x_d/10)}")
                if np.abs(y_d) > 5:
                    resp = requests.get(f"{server}/vertical?delta={-int(y_d/10)}")
                cv.imshow("img", img)
            except KeyboardInterrupt:
                cv.destroyAllWindows()
            if key == ord("q") or key == 27:
                print("Aborted Rotation")
                break
        cv.destroyAllWindows()

    def manual_remote_tracking(self):
        """Manually control the 2 DOF robotic arm with a keyboard
        """
        server = self._server
        i = 0
        while True:
            key = cv.waitKey(1)
            with timer:
                resp = requests.get(f"{server}/get_frame")
            print(timer.time)
            img = cv.imdecode(np.frombuffer(base64.b64decode(resp.content), dtype=np.uint8),
                              flags=cv.IMREAD_COLOR)
            if self._convert:
                img = img[:, :, ::-1]
            if key == 81:
                resp = requests.get(f"{server}/go_left")
                print("Going left")
            if key == 82:
                resp = requests.get(f"{server}/go_up")
                print("Going up")
            elif key == 83:
                resp = requests.get(f"{server}/go_right")
                print("Going right")
            elif key == 84:
                resp = requests.get(f"{server}/go_down")
                print("Going down")
            # elif key == ord("a"):
            #     print("Setting new Rotation")
            elif key == ord("q") or key == 27:
                print("Aborted Rotation")
                break
            try:
                # contours, mask = get_contours_and_mask_bgr(img, self._low_val, self._high_val)
                contours, mask = get_contours_and_mask_hsv(img, self._low_val, self._high_val)
                img = np.hstack([img, np.repeat(mask, 3).reshape(*mask.shape, 3)])
                cv.imshow("img", img)
                print(i)
                i += 1
            except KeyboardInterrupt:
                cv.destroyAllWindows()
        cv.destroyAllWindows()


if __name__ == '__main__':
    low_red = [163, 74, 30]
    high_red = [179, 255, 255]
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument("--no-bgr2rgb", dest="bgr2rgb", action="store_false")
    args = parser.parse_args()
    client = RemoteClient(args.host, args.port, img_size=[640, 480],
                          low_val=low_red, high_val=high_red)
    client.simple_agent()
