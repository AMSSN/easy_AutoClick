import copy

import xlrd
from lmTools import *
from AutoClick.Operations import SingleLeftClicker, SingleRightClicker, DoubleLeftClicker, DoubleRightClicker

OPSET = {
    "SingleLeftClicker": SingleLeftClicker,
    "SingleRightClicker": SingleRightClicker,
    "DoubleLeftClicker": DoubleLeftClicker,
    "DoubleRightClicker": DoubleRightClicker,
}
TYPES = ["", "SingleLeftClicker", "SingleRightClicker", "DoubleLeftClicker", "DoubleRightClicker"]
set_value("opset", OPSET)


class Cmd(object):
    def __init__(self, id):
        self.id = id
        self.last = None
        self.next = None
        self.operate = None


class OPFactory(object):
    """
    封装成一个工厂类，根据需求产出OP，而运行类只用一个静态的方法
    """

    def __init__(self):
        self.index = 1

    def create_cmd(self, last: [int, Cmd], operate) -> Cmd:
        """
            头OP的last_id=0，其本身id自动设为1
            创建一个OP时，只知道接在谁后面，并不知道下一个是谁。
        """
        new_op = Cmd(self.index)
        new_op.last = last
        new_op.operate = operate
        self.index += 1  # id自增
        # 对下一个OP进行链接
        if type(last) == Cmd:
            last.next = new_op
        last_id = last if type(last) == int else last.id
        logger.info(f"CreateOP id={self.index}\tlast_id={last_id}")
        return new_op


def run_cmd(start_cmd: Cmd):
    # 按照规则运行
    assert start_cmd.last == 0 and start_cmd.id == 1, "Please check start_op!"
    while start_cmd.next is not None:
        start_cmd.operate()
        start_cmd = start_cmd.next
    start_cmd.operate()


def check_xls(sheet1):
    """
    Cell的ctype含义
        0-XL_CELL_EMPTY-空单元格
        1-XL_CELL_TEXT-文本字符串
        2-XL_CELL_NUMBER-数字（浮点数）
        3-XL_CELL_DATE-日期或时间（需要通过 xlrd.xldate_as_tuple 转换为 Python 的日期时间对象）
        4-XL_CELL_BOOLEAN-布尔值（1 表示 True，0 表示 False）
        5-XL_CELL_ERROR-错误代码
        6-XL_CELL_BLANK-空白单元格（注意：空白单元格与空单元格不同）
    """
    check_res = True
    xls_ops = []
    # check rows
    if sheet1.nrows < 2:
        logger.error("lines num < 2, means no valid data in excel")
        check_res = False
    # check every lines
    i = 1
    while i < sheet1.nrows:
        # check operate type and data
        type_cell = sheet1.row(i)[0]
        data_cell = sheet1.row(i)[1]
        repeat_num_cell = sheet1.row(i)[2]
        # single or double click with left or right.
        if int(type_cell.value) == 1 or int(type_cell.value) == 2 or int(type_cell.value) == 3 or int(
                type_cell.value) == 4:
            if type_cell.ctype != 2 or data_cell.ctype == 0:
                check_res = False
            else:
                op_i = OPSET.get(TYPES[int(type_cell.value)])
                op_dict = {"type": op_i,
                           "data": data_cell.value,
                           "repeat_num": repeat_num_cell.value}
                xls_ops.append(op_dict)

        if not check_res:
            logger.error(f"row {i} type error or data error!")
        i += 1
    return check_res, xls_ops


# TODO 完成Operations.py后再完成该函数。
def gen_ops_from_xls(xls_path: str) -> [Cmd, None]:
    excel_file = xlrd.open_workbook(filename=xls_path)
    xls_folder = os.path.abspath(os.path.dirname(xls_path))
    # 通过索引获取表格sheet页
    sheet1 = excel_file.sheet_by_index(0)
    # 数据检查
    logger.info("check the sheet1 data...")
    check_res, xls_ops = check_xls(sheet1)
    if check_res:
        factory = OPFactory()
        # First op
        operate_instance = xls_ops[0]["type"](os.path.join(xls_folder, xls_ops[0]["data"]))
        start_op = factory.create_cmd(0, operate_instance)
        cmd_0 = start_op
        for i in range(1, len(xls_ops)):
            operate_instance = xls_ops[i]["type"](os.path.join(xls_folder, xls_ops[i]["data"]))
            cmd = factory.create_cmd(cmd_0, operate_instance)
            cmd_0 = cmd
        return start_op
    else:
        return None
