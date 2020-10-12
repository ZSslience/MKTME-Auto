import sys
import threading
import time
import traceback

from MiddleWare import lib_flash_server as lfs
from MiddleWare import lib_power_action_soundwave as lpa
from MiddleWare import lib_wmi_handler
from SoftwareAbstractionLayer import utils
from SoftwareAbstractionLayer import library
from SoftwareAbstractionLayer import lib_constants
from MiddleWare.lib_bios_config import BiosMenuConfig

import pythonsv_icx_handler as itp_sv

STEP_NO = 1
IS_CASE_PASS = True
TEST_CASE_ID = '1606777649'
SCRIPT_ID = '1606777649-1to11-Host.py'
FAIL_COLLECT = []

opt_wait_time = 5
os_boot_timeout = 120
boot_wait_timeout = 600
f2_timeout = 15

soundwave_port = utils.ReadConfig('SOUNDWAVE', 'PORT')
ifwi_release = utils.ReadConfig('IFWI_IMAGES', 'RELEASE')
logical_cores = int(utils.ReadConfig('1606777649', 'LOGICAL_CORES'))
max_active_thread = int(utils.ReadConfig('1606777649', 'MAX_ACTIVE_THREAD'))
wh = lib_wmi_handler.WmiHandler()
bios_conf = BiosMenuConfig(TEST_CASE_ID, SCRIPT_ID)


def result_process(result, step_string, test_exit=False, is_step_complete=True):
    global STEP_NO
    if not result:
        global IS_CASE_PASS
        IS_CASE_PASS = False
        if is_step_complete:
            print('#' * 160)
            library.write_log(lib_constants.LOG_FAIL, "Step %d: Failed to %s" % (STEP_NO, step_string),
                              TEST_CASE_ID, SCRIPT_ID)
            print('#' * 160)
            global FAIL_COLLECT
            FAIL_COLLECT.append((STEP_NO, step_string))
            STEP_NO += 1
        else:
            print('#' * 160)
            library.write_log(lib_constants.LOG_FAIL, "Failed to %s" % step_string,
                              TEST_CASE_ID, SCRIPT_ID)
            print('#' * 160)
        if test_exit:
            sys.exit(lib_constants.EXIT_FAILURE)
    else:
        if is_step_complete:
            print('#' * 160)
            library.write_log(lib_constants.LOG_INFO, "Step %d: Succeed to %s" % (STEP_NO, step_string),
                              TEST_CASE_ID, SCRIPT_ID)
            print('#' * 160)
            STEP_NO += 1
        else:
            print('#' * 160)
            library.write_log(lib_constants.LOG_INFO, "Succeed to %s" % step_string,
                              TEST_CASE_ID, SCRIPT_ID)
            print('#' * 160)


def log_write(result, info):
    if result == "PASS":
        library.write_log(lib_constants.LOG_PASS, 'Passed: %s' % info, TEST_CASE_ID, SCRIPT_ID)
        sys.exit(lib_constants.EXIT_SUCCESS)
    elif result == "FAIL":
        library.write_log(lib_constants.LOG_FAIL, 'Failed: %s' % info, TEST_CASE_ID, SCRIPT_ID)
        sys.exit(lib_constants.EXIT_FAILURE)
    elif result == "INFO":
        library.write_log(lib_constants.LOG_INFO, 'Status: %s' % info, TEST_CASE_ID, SCRIPT_ID)
        return True
    elif result == "DEBUG":
        library.write_log(lib_constants.LOG_DEBUG, 'Debug: %s' % info, TEST_CASE_ID, SCRIPT_ID)
        return True
    elif result == "WARNING":
        library.write_log(lib_constants.LOG_WARNING, 'Warning: %s' % info, TEST_CASE_ID, SCRIPT_ID)
        return True
    else:
        library.write_log(lib_constants.LOG_ERROR, 'Error: %s' % info, TEST_CASE_ID, SCRIPT_ID)
        return False


def is_boot_state():
    try:
        result = wh.wmi_os_opt(local=False, os_instruct="name")
        if "Windows" in result[0]:
            return "windows"
        else:
            return "na"
    except Exception:
        bios_conf.bios_control_key_press('ESC', 2, 3)
        is_efi = bios_conf.efi_shell_cmd("")
        if "Shell>" in is_efi:
            return "efi"
        elif "\\>" in is_efi:
            return "efi_fs"
        else:
            bios_conf.bios_control_key_press('ESC', 2, 2)
            result = bios_conf.bios_back_home()
            if result:
                return "bios"
            else:
                return "unknown"


def bios_init_opr():
    sut_state = is_boot_state()
    log_write('INFO', 'SUT is under %s state' % sut_state)
    if sut_state == 'bios':
        return True
    elif "efi" in sut_state:
        bios_conf.bios_control_key_press('CTRL_ALT_DELETE')
        enter_bios = bios_conf.enter_bios(boot_wait_timeout, f2_timeout)
        return enter_bios
    elif sut_state == 'windows':
        try:
            wh.wmi_os_opt(local=False, os_instruct="reboot")
            enter_bios = bios_conf.enter_bios(boot_wait_timeout, f2_timeout)
            return enter_bios
        except Exception:
            return False
    else:
        lpa.ac_off(soundwave_port)
        time.sleep(5)
        lpa.ac_on(soundwave_port)
        enter_bios = bios_conf.enter_bios(boot_wait_timeout, f2_timeout)
        return enter_bios


def test_boot_to_setup(step_string="Boot to BIOS Menu", complete=True):
    bios_boot = bios_init_opr()
    result_process(bios_boot, step_string, test_exit=True, is_step_complete=complete)


def itp_ctrl(status="open"):
    if status == "open":
        itp_sv.pythonsv_init()
        return True
    elif status == "close":
        itp_sv.pythonsv_exit()
        return True
    else:
        return False


def test_cpuid(id=0x7, idx=0, target="ecx", step_string="reading CPUID: ", complete=False):
    try:
        result = cpuid(id, idx)
        log_write("INFO", "cpuid %s, %s is %s" % (id, idx, result))
        target_val = result[target]
        log_write("INFO", "%s result is %s" % (target, target_val))
        result_process(True, "%s %s" % (step_string, id), test_exit=True, is_step_complete=complete)
        return target_val
    except Exception:
        result_process(False, "%s %s" % (step_string, id), test_exit=True, is_step_complete=complete)


def test_tme_set(value="Enable",
                 step_string="EDKII -> Socket Configuration -> Processor Configuration -> Total Memory Encryption ("
                             "TME): ",
                 complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Total Memory Encryption (TME)', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True,
                       is_step_complete=complete)


def test_mktme_set(value="Enable",
                   step_string="EDKII -> Socket Configuration -> Processor Configuration -> "
                               "Total Memory Encryption Multi-Tenant(TME-MT): ",
                   complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Total Memory Encryption Multi-Tenant(TME-MT)', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True,
                       is_step_complete=complete)


def test_directory_mode(step_string="EDKII Menu -> Socket Configuration -> Uncore Configuration -> "
                                    "Uncore General Configuration -> Directory Mode Enable",
                        complete=False):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Uncore Configuration",
                                  "Uncore General Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.get_system_information("Directory Mode Enable")
        result_process(result in ['Auto', 'Enable'], "%s %s" % (step_string, result), test_exit=True,
                       is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True,
                       is_step_complete=complete)


def disable_limit_pa46bits(value="Disable",
                           step_string="EDKII -> Socket Configuration -> Processor Configuration -> Limit CPU PA to "
                                       "46 bits",
                           complete=False):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Limit CPU PA to 46 bits', value)
        bios_conf.bios_save_changes()
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True,
                       is_step_complete=complete)


def test_bios_reset(flag=True, step_string="Save, reset, boot to BIOS", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        result = bios_conf.reset_to_bios(to_save=flag, wait_timeout=boot_wait_timeout, f2_press_wait=f2_timeout)
        result_process(result, step_string, test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True,
                       is_step_complete=complete)


def test_msr(id=0x35, step_string="reading MSR: ", complete=False):
    try:
        result = msr(id)
        return result
    except Exception:
        result_process(False, "%s %s" % (step_string, id), test_exit=True, is_step_complete=complete)


def test_itp_msr(id=0x982, idx=0, step_string="reading itp.threads.msr MSR: ", complete=False):
    try:
        result = itp.threads[idx].msr(id)
        return result
    except Exception:
        result_process(False, "%s %s" % (step_string, id), test_exit=True, is_step_complete=complete)


def test_flash_ifwi(image_for_flash, port='COM101', step_string="Flash the latest BIOS and boot to setup menu",
                    complete=True):
    os_state = is_boot_state()
    if os_state == "windows":
        wh.wmi_os_opt(local=False, os_instruct="shutdown")
    try:
        lfs.flashifwi_em100(binfile=image_for_flash, soundwave_port=port)
        lpa.ac_on(port)
        time.sleep(20)
        log_write('INFO', "IFWI flashed successfully with: %s" % image_for_flash)
    except Exception:
        result_process(False, step_string, test_exit=True, is_step_complete=complete)
    enter_bios = bios_conf.enter_bios(boot_wait_timeout, f2_timeout)
    result_process(enter_bios, step_string, test_exit=True, is_step_complete=complete)


def callback_logging():
    result_process(False, "Test case execution terminated due to timeout occurred", test_exit=True, is_step_complete=False)


def time_out(interval, callback=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            t = threading.Thread(target=func, args=args, kwargs=kwargs)
            t.setDaemon(True)
            t.start()
            t.join(interval)
            if t.is_alive() and callback:
                return threading.Timer(0, callback).start()
            else:
                return
        return wrapper
    return decorator


@time_out(1800, callback_logging)
def test_execution():
    # Step1: Flash IFWI and reset
    test_flash_ifwi(ifwi_release, complete=False)
    test_boot_to_setup(step_string="Flash the latest BIOS and boot to setup menu", complete=True)

    # Step 2: read CPUID(0x7, 0)
    itp_ctrl("open")
    result = test_cpuid(id=0x7, idx=0, target="ecx", step_string="reading CPUID 7.0.ECX bit 13", complete=False)
    r_bin = "{0:064b}".format(result)
    log_write('INFO', "Run result is %s" % r_bin)
    result_process(r_bin[-13] == "1", "Bit 13 of leaf 7 of ECX is 1", test_exit=True, is_step_complete=True)
    itp_ctrl("close")

    # Step 3: read CPUDID(0x80000008, 0)
    itp_ctrl("open")
    result = test_cpuid(id=0x80000008, idx=0, target="eax", step_string="Reading CPUID EAX", complete=False)
    r_bin = "{0:064b}".format(result)
    log_write('INFO', "EAX result is %s" % r_bin)
    result_process("1" in r_bin[-8:], "EAX is the maximum physical address: %s" % result,
                   test_exit=False, is_step_complete=True)
    itp_ctrl("close")

    # Step 4-5: Enable TME/MKTME
    test_tme_set()
    # Workaround to make MKTME work from sighting https://hsdes.intel.com/appstore/article/#/1508152249
    # Not necessary and may be removed in future.
    disable_limit_pa46bits()
    test_mktme_set()

    # Step 6: reset and check directory mode
    test_bios_reset(complete=False)
    test_directory_mode(complete=True)

    # Step 7: Check CPU cores and threads
    itp_ctrl("open")
    result = test_msr(id=0x35)
    itp_ctrl("close")
    result = "{0:064b}".format(result)
    core_count = int(result[-32:-16], 2)
    thread_count = int(result[-16:], 2)
    print(result, core_count, thread_count, core_count == logical_cores, thread_count == max_active_thread)
    result_process((core_count == logical_cores) and (thread_count == max_active_thread),
                   "Check the number of CPU active logical processor.", test_exit=True, is_step_complete=True)

    # Step 8: Check MSR 0x981
    itp_ctrl("open")
    msr_981_core_0 = test_itp_msr(id=0x981, idx=0)
    msr_981_core_max = test_itp_msr(id=0x981, idx=(max_active_thread - 1))
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_981_core_0)
    log_write("INFO", "MSR Info: thread 0 0x981: %s, thread max 0x981: %s, thread 0 binary converted: %s" % (
        msr_981_core_0, msr_981_core_max, r_bin))
    result = [msr_981_core_0 == msr_981_core_max, "1" == r_bin[-1], "1" in r_bin[-36:-32], "1" in r_bin[-51:-36]]
    result_process(False not in result, "Check the value of IA32_TME_CAPABILITY MSR 0x981",
                   test_exit=True, is_step_complete=True)

    # Step 9: Check MSR 0x982
    itp_ctrl("open")
    msr_982_core_0 = test_itp_msr(id=0x982, idx=0)
    msr_982_core_max = test_itp_msr(id=0x982, idx=(max_active_thread - 1))
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_982_core_0)
    log_write("INFO", "MSR Info: thread 0 0x982: %s, thread max 0x982: %s, thread 0 binary converted: %s" % (
        msr_982_core_0, msr_982_core_max, r_bin))
    result = [msr_982_core_0 == msr_982_core_max,
              "1" == r_bin[-1], "1" == r_bin[-2],
              "0" == r_bin[-3], "1" == r_bin[-4],
              "1" not in r_bin[-8:-4],
              "1" in r_bin[-36:-32],
              "1" == r_bin[-49]]
    result_process(False not in result, "Check the value of IA32_TME_ACTIVATE MSR 0x982",
                   test_exit=True, is_step_complete=True)

    # Step 10: Disable TME and check MSR 0x982
    test_tme_set(value="Disable", complete=False)
    test_bios_reset(complete=False)
    itp_ctrl("open")
    msr_982_core_0 = test_itp_msr(id=0x982, idx=0)
    msr_982_core_max = test_itp_msr(id=0x982, idx=(max_active_thread - 1))
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_982_core_0)
    log_write("INFO", "MSR Info: thread 0 0x982: %s, thread max 0x982: %s, thread 0 binary converted: %s" % (
        msr_982_core_0, msr_982_core_max, r_bin))
    result = [msr_982_core_0 == msr_982_core_max,
              "1" == r_bin[-1],
              "0" == r_bin[-2],
              r_bin[-36:-32] == "0000"]
    result_process(False not in result, "Check the value of IA32_TME_ACTIVATE MSR 0x982 when disable TME",
                   test_exit=True, is_step_complete=True)

    # Step 11: Enable TME but disable MKTME and check MSR 0x982
    test_tme_set(complete=False)
    test_mktme_set(value="Disable", complete=False)
    test_bios_reset(complete=False)
    itp_ctrl("open")
    msr_982_core_0 = test_itp_msr(id=0x982, idx=0)
    msr_982_core_max = test_itp_msr(id=0x982, idx=(max_active_thread - 1))
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_982_core_0)
    log_write("INFO", "MSR Info: thread 0 0x982: %s, thread max 0x982: %s, thread 0 binary converted: %s" % (
        msr_982_core_0, msr_982_core_max, r_bin))
    result = [msr_982_core_0 == msr_982_core_max,
              "1" == r_bin[-1],
              "1" == r_bin[-2],
              r_bin[-36:-32] == "0000"]
    result_process(False not in result,
                   "Check the value of IA32_TME_ACTIVATE MSR 0x982 when disable MKTME but enable TME",
                   test_exit=True,
                   is_step_complete=True)


def tear_down():
    sut_state = is_boot_state()
    if sut_state == "windows":
        wh.wmi_os_opt(local=False, os_instruct="shutdown")
    log_write("INFO", "Tear Down: SUT is under %s state, perform G3" % sut_state)
    lpa.ac_off(soundwave_port)
    time.sleep(5)


if __name__ == '__main__':
    try:
        test_execution()
    except Exception as e:
        result_process(False, "Exception Occurred: \r\n %s" % (traceback.format_exc()), test_exit=True,
                       is_step_complete=True)
    finally:
        tear_down()
        log_write('INFO', "%s steps executed with result verdict %s" % (STEP_NO - 1, IS_CASE_PASS))
        if len(FAIL_COLLECT) > 0:
            for i in FAIL_COLLECT:
                print("Failed Step(s): %s" % str(i))
        if IS_CASE_PASS:
            log_write('PASS', "Test Case %s Execution Finished" % TEST_CASE_ID)
        else:
            log_write('FAIL', "Test Case %s Execution Finished" % TEST_CASE_ID)
