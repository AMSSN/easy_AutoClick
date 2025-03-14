from lmTools import *
import os

from AutoClick.Commands import MyCommands

if __name__ == '__main__':
    com = MyCommands()
    com.new_OP(1, None, 2, "", "")
    com.new_OP(2, None, 3, "", "")
    com.new_OP(3, None, 4, "", "")
    com.new_OP(4, None, 5, "", "")
    com.new_OP(5, None, None, "", "")
    com.run()
