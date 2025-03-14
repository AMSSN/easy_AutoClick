__version__ = "1.0.0"
__author__ = "jlm"

from lmTools.globalM import set_value, get_value
from lmTools.lm_log import log_path, log_init
import os

print("Welcome to using lmTools", "\nPlease set value:log_path")
lmlogger = log_init()

__all__ = ["os",  # 通用库
           "log_path", "lmlogger",  # log相关
           "set_value", "get_value"  # tools相关
           ]
