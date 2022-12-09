import base64

import requests
import numpy as np
import cv2 as cv
from common_pyutil.monitor import Timer


timer = Timer()


def show_live():
    while True:
        with timer:
            resp = requests.get("http://192.168.1.9:8080/get_frame")
        print(timer.time)
        img = cv.imdecode(np.frombuffer(base64.b64decode(resp.content), dtype=np.uint8),
                          flags=cv.IMREAD_COLOR)[:, :, ::-1]
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
