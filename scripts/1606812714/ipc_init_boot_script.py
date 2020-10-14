import sys
import os
from datetime import datetime, timedelta

print("----------------------- openipc init -----------------------")
sys.path.append(".")

sys.path.append(r'C:\pythonSV\sapphirerapids')

from sapphirerapids.startspr import *

power_control = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ac_on_off.py')


def ipc_init_boot_script(try_times=5):
    import svtools.common.pysv_config as common_pysv_config
    # import svtools.ipip
    # try:
    #     delta = datetime.today() - svtools.ipip.get_last_update()
    #     if delta > timedelta(days=7):
    #         print("------------")
    #         print("It has been more than 7 days since running update_tools.py")
    #         svtools.ipip.update_tools(r'C:\pythonSV\sapphirerapids')
    # except:
    #     import traceback
    #     print(traceback.format_exc())
    #     print("-------------")
    #     print("Error running update tools, skipping")
    #     print("-------------")

    CFG = common_pysv_config.init()

    try:
        print("---------------- ipc init ----------------")
        start_openipc(CFG)
        start_general(CFG)
        import_modules(CFG)
        add_to_main(CFG)

        print("---------------- Run boot script ----------------")

        import sapphirerapids.toolext.bootscript.boot as b
        for i in range(try_times):
            print('run boot script ----> [{}]'.format(i + 1))
            ret_number = b.go(ignore_security_straps=True, fuse_files="enable_txt.cfg")
            if ret_number == 0:
                return True
            # else:
            #     result = os.system(r'C:\Python27_x86\python.exe {} ac_off'.format(power_control))
            #     if not result:
            #         print('AC Off failed')
            #         return False
            #     result = os.system(r'C:\Python27_x86\python.exe {} ac_on'.format(power_control))
            #     if not result:
            #         print('AC on failed')
            #         return False
    except Exception as e:
        print("ipc_init except")
        print(e)

    return False


if __name__ == '__main__':
    result = ipc_init_boot_script(try_times=10)
    if result:
        exit(0)
    else:
        exit(1)