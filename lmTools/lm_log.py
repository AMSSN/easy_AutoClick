import logging
from logging.handlers import TimedRotatingFileHandler
import os

# 定义log文件存放路径
log_path = "log"  # 在哪里import，这里的log_path就是相对与哪里的路径


def log_init():
    if not os.path.isdir(log_path):
        os.makedirs(log_path)
    # 创建一个 logger
    logger = logging.getLogger("my_logger")
    logger.setLevel(logging.DEBUG)

    # 创建 TimedRotatingFileHandler，并设置文件名、滚动间隔和保留日志文件个数
    handler = TimedRotatingFileHandler(filename=log_path + "/logfile.log", when="midnight", interval=1, backupCount=7)
    handler.suffix = "%Y-%m-%d.log"
    handler.encoding = "utf-8"
    handler.setFormatter(logging.Formatter("[%(asctime)s - %(levelname)s] - %(message)s "))
    logger.addHandler(handler)

    # 输出日志
    logger.info("Logging file inited!")
    return logger
