from unittest import result
import torch
import pyautogui
import pygetwindow
import gc
import numpy as np
import cv2
import time
import win32api
import win32con
import pandas as pd
from utils.general import (cv2, non_max_suppression, xyxy2xywh)
from models.common import DetectMultiBackend
import dxcam
import cupy as cp

def smooth_mouse_move(x_move, y_move, speed=1):
    current_x, current_y = win32api.GetCursorPos()
    target_x = current_x + x_move
    target_y = current_y + y_move

    distance_x = target_x - current_x
    distance_y = target_y - current_y

    interpolation_steps = int(max(abs(distance_x), abs(distance_y)) / speed)
    if interpolation_steps <= 0:
        return

    step_size_x = distance_x / interpolation_steps
    step_size_y = distance_y / interpolation_steps

    for step in range(1, interpolation_steps + 1):
        new_mouse_x = current_x + int(step * step_size_x)
        new_mouse_y = current_y + int(step * step_size_y)

        win32api.SetCursorPos((new_mouse_x, new_mouse_y))
        time.sleep(0.01)




def main():
    # Portion of screen to be captured (This forms a square/rectangle around the center of screen)
    screenShotHeight = 320
    screenShotWidth = 320

    # For use in games that are 3rd person and character model interferes with the autoaim
    # EXAMPLE: Fortnite and New World
    aaRightShift = 0

    # Autoaim mouse movement amplifier
    aaMovementAmp = 0.6

    # Person Class Confidence
    confidence = 0.6

    # What key to press to quit and shutdown the autoaim
    aaQuitKey = "P"

    # If you want to main slightly upwards towards the head
    headshot_mode = True

    # Displays the Corrections per second in the terminal
    cpsDisplay = True

    # Set to True if you want to get the visuals
    visuals = True

    # Selecting the correct game window
    try:
        videoGameWindows = pygetwindow.getAllWindows()
        print("=== All Windows ===")
        for index, window in enumerate(videoGameWindows):
            # only output the window if it has a meaningful title
            if window.title != "":
                print("[{}]: {}".format(index, window.title))
        # have the user select the window they want
        try:
            userInput = int(input(
                "Please enter the number corresponding to the window you'd like to select: "))
        except ValueError:
            print("You didn't enter a valid number. Please try again.")
            return
        # "save" that window as the chosen window for the rest of the script
        videoGameWindow = videoGameWindows[userInput]
    except Exception as e:
        print("Failed to select game window: {}".format(e))
        return

    # Activate that Window
    activationRetries = 30
    activationSuccess = False
    while (activationRetries > 0):
        try:
            videoGameWindow.activate()
            activationSuccess = True
            break
        except pygetwindow.PyGetWindowException as we:
            print("Failed to activate game window: {}".format(str(we)))
            print("Trying again... (you should switch to the game now)")
        except Exception as e:
            print("Failed to activate game window: {}".format(str(e)))
            print("Read the relevant restrictions here: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow")
            activationSuccess = False
            activationRetries = 0
            break
        # wait a little bit before the next try
        time.sleep(3.0)
        activationRetries = activationRetries - 1
    # if we failed to activate the window then we'll be unable to send input to it
    # so just exit the script now
    if activationSuccess == False:
        return
    print("Successfully activated the game window...")

    # Setting up the screen shots
    sctArea = {"mon": 1, "top": videoGameWindow.top + (videoGameWindow.height - screenShotHeight) // 2,
                         "left": aaRightShift + ((videoGameWindow.left + videoGameWindow.right) // 2) - (screenShotWidth // 2),
                         "width": screenShotWidth,
                         "height": screenShotHeight}

    # Starting screenshoting engine
    left = aaRightShift + \
        ((videoGameWindow.left + videoGameWindow.right) // 2) - (screenShotWidth // 2)
    top = videoGameWindow.top + \
        (videoGameWindow.height - screenShotHeight) // 2
    right, bottom = left + screenShotWidth, top + screenShotHeight

    region = (left, top, right, bottom)

    camera = dxcam.create(region=region)
    if camera is None:
        print("""DXCamera failed to initialize. Some common causes are:
        1. You are on a laptop with both an integrated GPU and discrete GPU. Go into Windows Graphic Settings, select python.exe and set it to Power Saving Mode.
         If that doesn't work, then read this: https://github.com/SerpentAI/D3DShot/wiki/Installation-Note:-Laptops
        2. The game is an exclusive full screen game. Set it to windowed mode.""")
        return
    camera.start(target_fps=160, video_mode=True)

    # Calculating the center Autoaim box
    cWidth = sctArea["width"] / 2
    cHeight = sctArea["height"] / 2

    # Used for forcing garbage collection
    count = 0
    sTime = time.time()

    # Loading Yolo5 Small AI Model
    model = DetectMultiBackend('yolov5x.engine', device=torch.device(
        'cuda'), dnn=False, data='', fp16=True)
    stride, names, pt = model.stride, model.names, model.pt

    # Used for colors drawn on bounding boxes
    COLORS = np.random.uniform(0, 255, size=(1500, 3))

    # Main loop Quit if Q is pressed
    last_mid_coord = None
    with torch.no_grad():
        while win32api.GetAsyncKeyState(ord(aaQuitKey)) == 0:

            npImg = cp.array([camera.get_latest_frame()])
            im = npImg / 255
            im = im.astype(cp.half)

            im = cp.moveaxis(im, 3, 1)
            im = torch.from_numpy(cp.asnumpy(im)).to('cuda')

            # # Converting to numpy for visuals
            # im0 = im[0].permute(1, 2, 0) * 255
            # im0 = im0.cpu().numpy().astype(np.uint8)
            # # Image has to be in BGR for visualization
            # im0 = cv2.cvtColor(im0, cv2.COLOR_RGB2BGR)

            # Detecting all the objects
            results = model(im)

            pred = non_max_suppression(
                results, confidence, confidence, 0, False, max_det=10)

            targets = []
            for i, det in enumerate(pred):
                s = ""
                gn = torch.tensor(im.shape)[[0, 0, 0, 0]]
                if len(det):
                    for c in det[:, -1].unique():
                        n = (det[:, -1] == c).sum()  # detections per class
                        s += f"{n} {names[int(c)]}, "  # add to string

                    for *xyxy, conf, cls in reversed(det):
                        targets.append((xyxy2xywh(torch.tensor(xyxy).view(
                            1, 4)) / gn).view(-1).tolist() + [float(conf)])  # normalized xywh

            targets = pd.DataFrame(
                targets, columns=['current_mid_x', 'current_mid_y', 'width', "height", "confidence"])

            # If there are people in the center bounding box
            if len(targets) > 0:
                # Get the last persons mid coordinate if it exists
                if last_mid_coord:
                    targets['last_mid_x'] = last_mid_coord[0]
                    targets['last_mid_y'] = last_mid_coord[1]
                    # Take distance between current person mid coordinate and last person mid coordinate
                    targets['dist'] = np.linalg.norm(
                        targets.iloc[:, [0, 1]].values - targets.iloc[:, [4, 5]], axis=1)
                    targets.sort_values(by="dist", ascending=False)

                # Take the first person that shows up in the dataframe (Recall that we sort based on Euclidean distance)
                xMid = targets.iloc[0].current_mid_x + aaRightShift
                yMid = targets.iloc[0].current_mid_y

                box_height = targets.iloc[0].height
                if headshot_mode:
                    headshot_offset = box_height * 0.38
                else:
                    headshot_offset = box_height * 0.2

                mouseMove = [xMid - cWidth, (yMid - headshot_offset) - cHeight]

                # Moving the mouse
                if win32api.GetKeyState(0x14):
                    smooth_mouse_move(int(mouseMove[0] * aaMovementAmp), int(mouseMove[1] * aaMovementAmp), speed=1)
                last_mid_coord = [xMid, yMid]

            else:
                last_mid_coord = None

            # See what the bot sees
            if visuals:
                npImg = cp.asnumpy(npImg[0])
                # Loops over every item identified and draws a bounding box
                for i in range(0, len(targets)):
                    halfW = round(targets["width"][i] / 2)
                    halfH = round(targets["height"][i] / 2)
                    midX = targets['current_mid_x'][i]
                    midY = targets['current_mid_y'][i]
                    (startX, startY, endX, endY) = int(
                        midX + halfW), int(midY + halfH), int(midX - halfW), int(midY - halfH)

                    idx = 0
                    # draw the bounding box and label on the frame
                    label = "{}: {:.2f}%".format(
                        "Human", targets["confidence"][i] * 100)
                    cv2.rectangle(npImg, (startX, startY), (endX, endY),
                                  COLORS[idx], 2)
                    y = startY - 15 if startY - 15 > 15 else startY + 15
                    cv2.putText(npImg, label, (startX, y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)

            # Forced garbage cleanup every second
            count += 1
            if (time.time() - sTime) > 1:
                if cpsDisplay:
                    print("CPS: {}".format(count))
                count = 0
                sTime = time.time()

            # Uncomment if you keep running into memory issues
            # gc.collect(generation=0)

            # See visually what the Aimbot sees
            if visuals:
                cv2.imshow('Live Feed', npImg)
                if (cv2.waitKey(1) & 0xFF) == ord('q'):
                    exit()
    camera.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("Please read the below message and think about how it could be solved before posting it on discord.")
        traceback.print_exception(e)
        print(str(e))
        print("Please read the above message and think about how it could be solved before posting it on discord.")
