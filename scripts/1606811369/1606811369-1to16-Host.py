import os
import re
import sys
import time
import threading
import traceback

from HardwareAbstractionLayer import hal_serial_opt as hso
# from MiddleWare import lib_wmi_handler
from MiddleWare import lib_flash_server as lfs
from MiddleWare import lib_power_action_soundwave as lpa
from MiddleWare.lib_bios_config import BiosMenuConfig
from SoftwareAbstractionLayer import utils
from SoftwareAbstractionLayer import library
from SoftwareAbstractionLayer import lib_constants

import pythonsv_icx_handler as itp_sv
# 1606811369 [PreSi & PostSi][MKTME] To Check if MKTME is able to exclude addresses.
# rev.26

# Constants Definition
TEST_CASE_ID = "1606811369"
SCRIPT_ID = "1606811369-1to16-Host.py"
IS_CASE_PASS = True
STEP_NO = 1
FAIL_COLLECT = []

# Variants Definition
opt_wait_time = 60
os_boot_timeout = 120
boot_wait_timeout = 600
f2_timeout = 120
esc_timeout = 60
save_timeout = 150
sut_host = utils.ReadConfig('SUT_IP', 'target_sut_ip')
usb_drive_label = utils.ReadConfig('USB Drive', 'DRIVE_LETTER')
usb_drive_alias = utils.ReadConfig('USB Drive', 'EFI_ALIAS')
ifwi_release = utils.ReadConfig('IFWI_IMAGES', 'RELEASE')
soundwave_port = utils.ReadConfig('SOUNDWAVE', 'PORT')
logical_cores = int(utils.ReadConfig('1606811369', 'LOGICAL_CORES'))
max_active_thread = int(utils.ReadConfig('1606811369', 'MAX_ACTIVE_THREAD'))
# wh = lib_wmi_handler.WmiHandler()
hs = hso.SerialComm()
bios_conf = BiosMenuConfig(TEST_CASE_ID, SCRIPT_ID)

# Test Case Steps Abstraction


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
        print("STEP_NO: %s, IS_CASE_PASS: %s" % (str(STEP_NO), str(IS_CASE_PASS)))
        print("FAIL_COLLECT:")
        print(FAIL_COLLECT)
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
        library.write_log(lib_constants.LOG_PASS, 'Passed: %s' % (info), TEST_CASE_ID, SCRIPT_ID)
        sys.exit(lib_constants.EXIT_SUCCESS)
    elif result == "FAIL":
        library.write_log(lib_constants.LOG_FAIL, 'Failed: %s' % (info), TEST_CASE_ID, SCRIPT_ID)
        sys.exit(lib_constants.EXIT_FAILURE)
    elif result == "INFO":
        library.write_log(lib_constants.LOG_INFO, 'Status: %s' % (info), TEST_CASE_ID, SCRIPT_ID)
        return True
    elif result == "DEBUG":
        library.write_log(lib_constants.LOG_DEBUG, 'Debug: %s' % (info), TEST_CASE_ID, SCRIPT_ID)
        return True
    elif result == "WARNING":
        library.write_log(lib_constants.LOG_WARNING, 'Warning: %s' % (info), TEST_CASE_ID, SCRIPT_ID)
        return True
    else:
        library.write_log(lib_constants.LOG_ERROR, 'Error: %s' % (info), TEST_CASE_ID, SCRIPT_ID)
        return False


def is_boot_state():
    bios_conf.bios_control_key_press('ESC', 2, esc_timeout)
    is_efi = bios_conf.efi_shell_cmd("")
    if "Shell>" in is_efi:
        return "efi"
    elif "\\>" in is_efi:
        return "efi_fs"
    else:
        bios_conf.bios_control_key_press('ESC', 2, esc_timeout)
        result = bios_conf.bios_back_home()
        if result:
            return "bios"
        else:
            return "unknown"


def tear_down():
    sut_state = is_boot_state()
    log_write("INFO", "Tear Down: SUT is under %s state, perform G3" % sut_state)
    lpa.ac_off(soundwave_port)
    time.sleep(5)


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


def test_flash_ifwi(image_for_flash, port='COM101', step_string="Flash the latest BIOS and boot to setup menu",
                    complete=True):
    try:
        lfs.flashifwi_em100(binfile=image_for_flash, soundwave_port=port)
        lpa.ac_on(port)
        time.sleep(20)
        log_write('INFO', "IFWI flashed successfully with: %s" % image_for_flash)
    except Exception:
        result_process(False, step_string, test_exit=True, is_step_complete=complete)
    enter_bios = bios_conf.enter_bios(boot_wait_timeout, f2_timeout)
    result_process(enter_bios, step_string, test_exit=True, is_step_complete=complete)


def test_boot_to_setup(step_string="Boot to BIOS Menu", complete=True):
    bios_boot = bios_init_opr()
    result_process(bios_boot, step_string, test_exit=True, is_step_complete=complete)


def itp_ctrl(status="open"):
    if status == "open":
        itp_sv.pythonsv_init()
        return itp, sv
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


def test_itp_msr(id=0x982, idx=0, step_string="reading itp.threads.msr MSR: ", complete=False):
    try:
        result = itp.threads[idx].msr(id)
        return result
    except Exception:
        result_process(False, "%s %s" % (step_string, id), test_exit=True, is_step_complete=complete)


def test_msr(id=0x35, step_string="reading MSR: ", complete=False):
    try:
        result = msr(id)
        return result
    except Exception:
        result_process(False, "%s %s" % (step_string, id), test_exit=True, is_step_complete=complete)


def test_bios_reset(flag=True, step_string="Save, reset, boot to BIOS", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        result = bios_conf.reset_to_bios(to_save=flag, wait_timeout=boot_wait_timeout, f2_press_wait=f2_timeout)
        result_process(result, step_string,
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_aesni_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> AES-NI: ",
                   complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('AES-NI', value)
        bios_conf.bios_save_changes(wait_time=save_timeout)
        result_process(result, "%s %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_tme_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> "
                                             "Total Memory Encryption (TME): ",
                 complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Total Memory Encryption (TME)', value)
        bios_conf.bios_save_changes(wait_time=save_timeout)
        result_process(result, "%s %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_mktme_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> "
                                               "Total Memory Encryption Multi-Tenant(TME-MT): ",
                   complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Total Memory Encryption Multi-Tenant(TME-MT)', value)
        bios_conf.bios_save_changes(wait_time=save_timeout)
        result_process(result, "%s %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_dimm_mngment(value="BIOS Setup", step_string="EDKII -> Socket Configuration -> Memory Configuration -> "
                                                      "Memory Dfx Configuration -> DIMM Management",
                      complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Memory Configuration",
                                  "Memory Dfx Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('DIMM Management', value)
        bios_conf.bios_save_changes(wait_time=save_timeout)
        result_process(result, "%s: %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_mem_app_direct(value="Disable",
                        step_string="EDKII -> Socket Configuration -> Memory Configuration ->"
                                    " Memory Dfx Configuration -> AppDirect",
                        complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Memory Configuration",
                                  "Memory Dfx Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('AppDirect', value)
        bios_conf.bios_save_changes(wait_time=save_timeout)
        result_process(result, "%s: %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_tme_addr_set(value="1000", step_string="Providing our own address to be exclude from the encrypting through MKTME",
                      complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration",
                                  "Processor Dfx Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_textbox_input('TME Exclusion Base Address Increment Value', value)
        result = bios_conf.bios_opt_textbox_input('TME Exclusion Length Increment value', value)
        bios_conf.bios_save_changes(wait_time=save_timeout)
        result_process(result, "%s: %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_volatile_mem_mode(value="1LM", step_string="Set CR DIMMs in the 1LM mode", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Memory Configuration", "Memory Map"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Volatile Memory Mode', value)
        bios_conf.bios_save_changes(wait_time=save_timeout)
        result_process(result, "%s: %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)





def callback_logging():
    result_process(False, "Test case execution terminated due to timeout occurred",
                   test_exit=True, is_step_complete=False)


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


@time_out(7200, callback_logging)
# Test Case Execution
def test_execution():
    # Test Run Start
    # Step 1: flash ifwi and boot to setup
    test_flash_ifwi(ifwi_release, complete=False)
    test_boot_to_setup(step_string="Flash the latest BIOS and boot to setup menu")

    # Step 2: enable AES-NI/TME/MKTME
    test_aesni_set(complete=False)
    test_tme_set(complete=False)
    test_mktme_set(complete=False)
    test_bios_reset()

    # Step 3: check MSR 0x35
    itp_ctrl("open")
    result = test_msr(id=0x35)
    itp_ctrl("close")
    result = "{0:064b}".format(result)
    core_count = int(result[-32:-16], 2)
    thread_count = int(result[-16:], 2)
    print(result, core_count, thread_count, core_count == logical_cores, thread_count == max_active_thread)
    result_process((core_count == logical_cores) and (thread_count == max_active_thread),
                   "Check the number of CPU active logical processor.",
                   test_exit=True, is_step_complete=True)

    # Step 4: check MSR 0x983
    itp_ctrl("open")
    msr_983_core_0 = test_itp_msr(id=0x983, idx=0)
    msr_983_core_max = test_itp_msr(id=0x983, idx=(max_active_thread-1))
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_983_core_0)
    log_write("INFO", "MSR Info: thread 0 0x983: %s, thread max 0x983: %s, thread 0 binary converted: %s" % (
        msr_983_core_0, msr_983_core_max, r_bin))
    result = [msr_983_core_0 == msr_983_core_max, "1" not in r_bin]
    print(result)
    result_process(False not in result, "Check the value of ACTIVATION MSR 0x983",
                   test_exit=True, is_step_complete=True)

    # Step 5: Check MSR 0x984
    itp_ctrl("open")
    msr_984_core_0 = test_itp_msr(id=0x984, idx=0)
    msr_984_core_max = test_itp_msr(id=0x984, idx=(max_active_thread-1))
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_984_core_0)
    log_write("INFO", "MSR Info: thread 0 0x984: %s, thread max 0x984: %s, thread 0 binary converted: %s" % (
        msr_984_core_0, msr_984_core_max, r_bin))
    result = [msr_984_core_0 == msr_984_core_max, "1" not in r_bin]
    print(result)
    result_process(False not in result, "Check the value of ACTIVATION MSR 0x984",
                   test_exit=True, is_step_complete=True)

    # Step 6: Set DIMM Managerment to BIOS Setup
    test_dimm_mngment()

    # Step 7: Disable AppDirect
    test_mem_app_direct()

    # Step 8: set exclude addr and save and reset
    test_tme_addr_set(complete=False)
    test_bios_reset()

    # Step 9: check MSR 0x984
    itp_ctrl("open")
    msr_984_core_0 = test_itp_msr(id=0x984, idx=0)
    msr_984_core_max = test_itp_msr(id=0x984, idx=(max_active_thread-1))
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_984_core_0)
    log_write("INFO", "MSR Info: thread 0 0x984: %s, thread max 0x984: %s, thread 0 binary converted: %s" % (
        msr_984_core_0, msr_984_core_max, r_bin))
    result = [msr_984_core_0 == msr_984_core_max, "1000000000000" == r_bin[-13:]]
    print(result)
    result_process(False not in result, "Check the value of ACTIVATION MSR 0x984",
                   test_exit=True, is_step_complete=True)

    # Step 10: check MSR 0x983
    itp_ctrl("open")
    msr_983_core_0 = test_itp_msr(id=0x983, idx=0)
    msr_983_core_max = test_itp_msr(id=0x983, idx=(max_active_thread-1))
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_983_core_0)
    log_write("INFO", "MSR Info: thread 0 0x983: %s, thread max 0x983: %s, thread 0 binary converted: %s" % (
        msr_983_core_0, msr_983_core_max, r_bin))
    result = [msr_983_core_0 == msr_983_core_max, "0x000FFFFFFFFFF800" in str(msr_983_core_0), "1" == r_bin[-12]]
    print(result)
    result_process(False not in result, "Check the value of ACTIVATION MSR 0x983",
                   test_exit=True, is_step_complete=True)

    ## No CR DIMM for EGS, so skip the rest steps
    # result_process(True, "Now, Power down the System to plug in the CR Dimms available as per Whitley-pdg memory population rule like DRAM + BPS(128G): 1+ 1 configuration: Already configured in bench")
    # test_volatile_mem_mode()
    # result_process(True, "Skip: EDKII -> Socket Configuration -> Memory Configuration -> Memory Dfx Configuration -> AppDirect: Disable as already set")
    # test_tme_addr_set(value="2000")
    # bios_conf.bios_initialize(wait_timeout=boot_wait_timeout, f2_press_wait=f2_timeout)
    # itp_ctrl("open")
    # msr_984_core_0 = test_itp_msr(id=0x984, idx=0)
    # msr_984_core_max = test_itp_msr(id=0x984, idx=(max_active_thread-1))
    # itp_ctrl("close")
    # r_bin = "{0:064b}".format(msr_984_core_0)
    # log_write("INFO", "MSR Info: thread 0 0x984: %s, thread max 0x984: %s, thread 0 binary converted: %s" % (msr_984_core_0, msr_984_core_max, r_bin))
    # result = [msr_984_core_0 == msr_984_core_max, "10000000000000" == r_bin[-14:]]
    # print(result)
    # result_process(False not in result, "Check the value of ACTIVATION MSR 0x984", test_exit=True, is_step_complete=True)
    #
    # itp_ctrl("open")
    # msr_983_core_0 = test_itp_msr(id=0x983, idx=0)
    # msr_983_core_max = test_itp_msr(id=0x983, idx=(max_active_thread-1))
    # itp_ctrl("close")
    # r_bin = "{0:064b}".format(msr_983_core_0)
    # log_write("INFO", "MSR Info: thread 0 0x983: %s, thread max 0x983: %s, thread 0 binary converted: %s" % (msr_983_core_0, msr_983_core_max, r_bin))
    # result = [msr_983_core_0 == msr_983_core_max, "0x000FFFFFFFFFE800" in str(msr_983_core_0), "1" == r_bin[-12]]
    # print(result)
    # result_process(False not in result, "Check the value of ACTIVATION MSR 0x983", test_exit=True, is_step_complete=True)
    

if __name__ == "__main__":
    try:
        test_execution()
    except Exception:
        result_process(False, "Exception Occurred: \r\n %s" % (traceback.format_exc()),
                       test_exit=True, is_step_complete=True)
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