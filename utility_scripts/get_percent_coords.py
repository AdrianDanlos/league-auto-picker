# flake8: noqa: E501
# THIS IS A HELPER SCRIPT TO GET THE PERCENTAGE COORDINATES OF THE CHAMP SELECT WINDOW.
# NOT USED ON THE MAIN SCRIPT
import pyautogui
import pygetwindow as gw
import keyboard

print("Move your mouse to the desired spot inside the League client.")
print("Press 's' to record the position...")

while True:
    if keyboard.is_pressed("s"):
        break

x, y = pyautogui.position()
windows = gw.getWindowsWithTitle("League of Legends")
if not windows:
    print("League of Legends client window not found.")
    exit(1)
win = windows[0]

percent_x = (x - win.left) / win.width
percent_y = (y - win.top) / win.height

print(f'"x": {percent_x:.4f}, "y": {percent_y:.4f}')
