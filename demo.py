import xlrd

from AutoClick.SmartRec import locate_screen_by_image
from lmTools import *
from AutoClick import *

from AutoClick.Commands import OPFactory, run_cmd, check_xls, gen_ops_from_xls

if __name__ == '__main__':
    factory = OPFactory()
    # op1 = factory.create_op(0, "", "")
    # op2 = factory.create_op(op1, "", "")
    # op3 = factory.create_op(op2, "", "")
    # op4 = factory.create_op(op3, "", "")
    # op5 = factory.create_op(op4, "", "")
    # op6 = factory.create_op(op5, "", "")
    # run_OPs(op1)

    start_cmd = gen_ops_from_xls("xlsInput/cmd.xls")
    run_cmd(start_cmd)
    # x,y = locate_screen_by_image("xlsInput/start.png")
    # print(x,y)