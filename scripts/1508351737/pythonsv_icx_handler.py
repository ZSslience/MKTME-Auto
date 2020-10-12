import sys

print("----------------------- pythonsv project init -----------------------")
sys.path.append(".")
sys.path.append(r'C:\PythonSV\icelakex')

from icelakex.starticx import *
from svtools.common.pysv_config import CFG


def pythonsv_init(try_times=5):
    for i in range(try_times):
        try:
            start_openipc(CFG)
            start_general(CFG)
            print(">>>>>>>> itp.halt()")
            itp = get_itp()
            itp.halt()
            print(">>>>>>>> itp.halt() success")
            print(">>>>>>>> sv.fresh()")
            sv = get_sv()
            sv.refresh()
            print(">>>>>>>> sv.refresh() success")
            return itp, sv
        except Exception as e:
            print("exception occurred")
            print(e)
            continue


def get_cpuid(try_times=5):
    for i in range(try_times):
        try:
            start_openipc(CFG)
            start_general(CFG)
            print(">>>>>>>> cupid(0x7,0)")
            halt()
            result = cpuid(0x7,0)
            return result
        except Exception as e:
            print("ipc_init except")
            print(e)
            continue


def pythonsv_exit(try_times=5):
    for i in range(try_times):
        try:
            start_openipc(CFG)
            start_general(CFG)

            print(">>>>>>>> itp.go")
            itp = get_itp()
            itp.go()
            # exit()
            return True
        except Exception as e:
            print("ipc_init except")
            print(e)
            continue
    return False

