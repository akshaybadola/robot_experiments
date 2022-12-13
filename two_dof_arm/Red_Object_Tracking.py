import cv2
import numpy as np

def gstreamer_pipeline(width=512, height=512, flip_180=False):
    args = ["libcamerasrc", f"video/x-raw, width={width}, height={height}"]
    if flip_180:
        args.append("videoflip method=rotate-180")
    args.append("appsink")
    return (" ! ".join(args))

ht = 320
wd = 480


_gst_pipeline = gstreamer_pipeline(wd, ht, flip_180=True)
cap=cv2.VideoCapture(_gst_pipeline, cv2.CAP_GSTREAMER)

#cap.set(3, wd)
#cap.set(4, ht)

ret,frame = cap.read()
rows, cols, ch = frame.shape
x_medium = int(cols / 2)
y_medium = int(rows / 2)

x_center = int(cols / 2)
y_center = int(rows / 2)

x_position = 90
y_position = 90

x_band = 50
y_band = 50


while ret == True:
    ret,frame1 = cap.read()
    frame2 = cv2.flip(frame1, 1)
#     frame2 = cv2.flip(frame, 0)
    
    hsv_frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2HSV)
    
    low_red = np.array([163, 74, 30])
    high_red = np.array([179, 255, 255])
    
    red_mask = cv2.inRange(hsv_frame2, low_red, high_red)
    red = cv2.bitwise_and(frame2, frame2, mask = red_mask)
    
    contours_red,_ = cv2.findContours(red_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours_red, key=lambda x:cv2.contourArea(x), reverse=True) # Arrange Contours in Assending
    for cnt in contours: # Draw rectangle on First contors on image
        (x,y,w,h) = cv2.boundingRect(cnt)
        cv2.rectangle(frame2, (x , y) , (x + w, y + h) , (0, 255, 0), 2) # Getting Position of rectangle & line colour & thickness
        break # Br
        
    for cnt in contours:
        (x,y,w,h) = cv2.boundingRect(cnt)
        x_medium = int((x + x + w) / 2) # Checking horizontal center of red object & save to variable
        y_medium = int((y + y + h) / 2) # Checking Vertical center of red object & save to variable
        break
        
    cv2.line(frame2, (x_medium, 0), (x_medium, ht), (0, 255, 0), 2) #Draw horizontal centre line of red object
    cv2.line(frame2, (0, y_medium), (wd, y_medium), (0, 255, 0), 2) #Draw Vertical centre line of red object
    cv2.imshow("IN Frame", frame2) #
    
    if x_medium < x_center - x_band:
        x_position -= 1
    elif x_medium > x_center + x_band:
        x_position += 1


    if y_medium < y_center - y_band:
        y_position -= 1
    elif y_medium > y_center + y_band:
        y_position += 1

    if x_position >= 180:
        x_position = 180
    elif x_position <+ 0:
        x_position = 0
    else:
        x_position = x_position
    if y_position >= 180:
        y_position = 180
    elif y_position <= 0:
        y_position = 0
    else:
        y_position = y_position


    print("X-{}, Y-{}".format(x_position, y_position))

    key = cv2.waitKey(1)
    if key == ord('q'):
        break


cv2.destroyAllWindows()
cap.release()
    
