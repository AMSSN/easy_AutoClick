import xlrd
import time
from utils import dataCheck, wholeWork
import lmTools



if __name__ == '__main__':
    logger = lmTools.get_value("logger")
    logger.info("欢迎使用Auto-Click脚本(cover by不高兴就喝水牌RPA~)")
    # 通过路径打开文件
    try:
        file = 'xlsInput/cmd.xls'
        excel_file = xlrd.open_workbook(filename=file)
        # 通过索引获取表格sheet页
        sheet1 = excel_file.sheet_by_index(0)
        # 大task之间的间隔(s)
        taskDur = 1
        # 数据检查
        logger.info("check the sheet1 data...")
        checkCmd = dataCheck(sheet1)
        if checkCmd:
            logger.info("check the sheet1 data success!")
            key = input('选择功能:\n 1.只做一次 2.无限循环 \n')
            if key == '1':
                # 循环拿出每一行指令
                wholeWork(sheet1)
            elif key == '2':
                while True:
                    try:
                        wholeWork(sheet1)
                        logger.info("操作成功，等待" + str(taskDur) + "秒")
                    except:
                        logger.info("操作失败，等待" + str(taskDur) + "秒")
                        time.sleep(taskDur)
    except Exception as e:
        logger.error(e)
        logger.error("open excel file failed!")
        print("failed!")
