import pyautogui

from AutoClick.SmartRec import locate_screen_by_image
from lmTools import *


class Operate:
    def __init__(self):
        self.repeat_num = 1
        pass

    def __call__(self, *args, **kwargs):
        pass


class SingleLeftClicker(Operate):
    def __init__(self, img):
        super().__init__()
        self.locate_x, self.locate_y = locate_screen_by_image(img)

    def __call__(self, *args, **kwargs):
        pyautogui.click(self.locate_x,
                        self.locate_y,
                        clicks=1,
                        interval=0.2,
                        duration=0.2,
                        button='LEFT')


class SingleRightClicker(SingleLeftClicker):
    def __init__(self, img):
        super().__init__(img)

    def __call__(self, *args, **kwargs):
        pyautogui.click(self.locate_x,
                        self.locate_y,
                        clicks=1,
                        interval=0.2,
                        duration=0.2,
                        button='RIGHT')


class DoubleLeftClicker(SingleLeftClicker):
    def __init__(self, img):
        super().__init__(img)

    def __call__(self, *args, **kwargs):
        pyautogui.click(self.locate_x,
                        self.locate_y,
                        clicks=2,
                        interval=0.1,
                        duration=0.2,
                        button='LEFT')


class DoubleRightClicker(SingleLeftClicker):
    def __init__(self, img):
        super().__init__(img)

    def __call__(self, *args, **kwargs):
        pyautogui.click(self.locate_x,
                        self.locate_y,
                        clicks=2,
                        interval=0.1,
                        duration=0.2,
                        button='RIGHT')
