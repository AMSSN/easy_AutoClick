# Auto-Click

指令序列：1、excel配合image输入(传统)。2、可视化界面，拖拽方式(终极形态，友好交互)

智能识别：1、pyautogui库locateCenterOnScreen根据图片匹配桌面上的位置。2、yolo目标检测。

操作集：pyautogui库模拟鼠标、键盘输入。剪切板输入、热键(按键组合)输入。

**基础操作：**

单击、双击、选中、滑轮

文本输入(模拟键盘输入)

键盘(单个按键)

键盘(组合键)

#### SOP：

1、Operations.py中创建新的“操作”

2、同步更新Commands.py的OPSET、TYPES。注意TYPES的顺序要与xls里的说明一样。即xls里的“指令类型”是多少，TYPES列表里第几个元素就是该“操作”的类名。

3、在Commands.py的check_xls()里进行check操作，检查参数合法性，并拼接成op_dict后append到xls_ops里，



#### 2025.3.13

log功能单独封装成一个包，方便使用。(已经封装在lmTools包内)

自动点击的核心是“按照一系列的指令模拟外设输入”，核心分为3块：指令序列，智能识别，操作集。最后的控制器作为程序的入口。

#### 2025.3.14

完成鼠标点击的基本操作，并测试通过。











#### TODO

封装配置类，全局变量，用于控制一些参数，比如“pyautogui.locateCenterOnScreen(img, confidence=0.9)”



















