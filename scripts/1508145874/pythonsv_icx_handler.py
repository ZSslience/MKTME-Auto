import sys

print("----------------------- pythonsv project init -----------------------")
sys.path.append(".")
sys.path.append(r'C:\PythonSV\icelakex')

from icelakex.starticx import *
from icelakex.toolext import pysv_config
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


if __name__ == '__main__':
    itp, sv = pythonsv_init()
    # x = cpuid(0x7,0)
    # print(x)
    # print("ECX data: %s" % (hex(x['ecx'])))
    # ECX_BIN = "{0:08b}".format(x['ecx'])
    # print(ECX_BIN[-14] == "1")
    # ECX_DEC = x['ecx']
    # MASK_14 = 1 << 14
    # print(ECX_DEC, MASK_14)
    # EXPECT_MASK_14 = 0b1 << 14
    # print((ECX_DEC & MASK_14) == EXPECT_MASK_14)

    x = cpuid(0x80000008,0)
    print(x)

    # post_80 = itp.threads[0].port(0x80)
    # post_81 = itp.threads[0].port(0x81)
    # print("POST CODE: %s%s" % (post_80, post_81))
    x = itp.threads[0].msr(0x981)
    print("MSR 0x981: %s" % x)

    pythonsv_exit()
