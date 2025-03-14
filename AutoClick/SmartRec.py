from lmTools import *
import pyautogui

"""
yolo识别的时候才需要一个类来封装，普通的pyautogui识别只需要一个静态方法
"""


# class ScreenRec:
#     def __init__(self):
#         pass
#
#     def rec_location(self):
#         pass
#

# TODO 封装全局配置类，用于控制confidence等参数
def locate_screen_by_image(img):
    location = pyautogui.locateCenterOnScreen(img, confidence=0.9)
    if location is not None:
        return location.x, location.y
    else:
        return -1, -1
