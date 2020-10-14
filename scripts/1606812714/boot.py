import os
import re
import subprocess
import time

from MiddleWare import lib_power_action_soundwave as lpa


def boot_with_script():
    lpa.ac_on()
    time.sleep(5)
    launch_path = os.path.dirname(os.path.abspath(__file__))
    boot_script_path = os.path.abspath(os.path.join(launch_path, r'ipc_init_boot_script.py'))
    print("boot script path: {}".format(boot_script_path))

    python_path = r'C:\Python36\python.exe'
    cmd = '{} {}'.format(python_path, boot_script_path)
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    while p.poll() is None:
        p.stdout.flush()
        line = p.stdout.readline()
        if line:
            print(line.decode('utf8'))
            if re.search(rb'.*seconds to reach break: power_off', line, re.I):
                lpa.ac_off()
            elif re.search(rb'.*seconds to reach break: power_on', line, re.I):
                lpa.ac_on()
    if p.returncode == 0:
        print("Run boot script [Successful]")
        return True
    else:
        print("Run boot script [Failed]")
        return False


def reset_bios():
    lpa.ac_off()
    time.sleep(5)

    return boot_with_script()


if __name__ == '__main__':
    if boot_with_script():
        print('boot ok')
    else:
        print('boot nok')

    # print('Doing some testing work...')
    # time.sleep(30)
    # if reset_bios():
    #     print('reset bios ok')
    # else:
    #     print('reset bios nok')