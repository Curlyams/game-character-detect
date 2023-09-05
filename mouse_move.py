import time
import win32api
import win32con

def smooth_mouse_move(target_x, target_y, speed):
    # Get the current mouse position
    current_x, current_y = win32api.GetCursorPos()

    # Calculate the distance between the current and target positions
    distance_x = target_x - current_x
    distance_y = target_y - current_y

    # Calculate the number of steps for interpolation based on the desired speed
    interpolation_steps = int(max(abs(distance_x), abs(distance_y)) / speed)

    if interpolation_steps <= 0:
        return

    # Calculate the step sizes for each axis
    step_size_x = distance_x / interpolation_steps
    step_size_y = distance_y / interpolation_steps

    # Perform the interpolation
    for step in range(1, interpolation_steps + 1):
        # Calculate the new mouse position for the current step
        new_mouse_x = current_x + int(step * step_size_x)
        new_mouse_y = current_y + int(step * step_size_y)

        # Move the mouse to the new position
        win32api.SetCursorPos((new_mouse_x, new_mouse_y))

        # Delay between interpolation steps (adjust as needed)
        time.sleep(0.01)

# Update the mouse movement code
xMid = targets.iloc[0].current_mid_x + aaRightShift
yMid = targets.iloc[0].current_mid_y

box_height = targets.iloc[0].height
if headshot_mode:
    headshot_offset = box_height * 0.38
else:
    headshot_offset = box_height * 0.2

target_x = xMid - cWidth
target_y = (yMid - headshot_offset) - cHeight

# Moving the mouse
if win32api.GetKeyState(0x14):
    smooth_mouse_move(target_x * aaMovementAmp, target_y * aaMovementAmp, speed=10)

last_mid_coord = [xMid, yMid] if win32api.GetKeyState(0x14) else None
