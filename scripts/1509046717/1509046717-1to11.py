import sys
import time
import threading
import traceback
from MiddleWare import lib_flash_server as lfs
from MiddleWare import lib_power_action_soundwave as lpa
from MiddleWare.lib_bios_config import BiosMenuConfig
from SoftwareAbstractionLayer import utils
from SoftwareAbstractionLayer import library
from SoftwareAbstractionLayer import lib_constants
import pythonsv_icx_handler as itp_sv

# Constants Definition
TEST_CASE_ID = "1509046717"
SCRIPT_ID = "1509046717-1to11-Host.py"
IS_CASE_PASS = True
STEP_NO = 1
FAIL_COLLECT = []

# Variants Definition
opt_wait_time = 60
boot_wait_timeout = 600
f2_timeout = 120
esc_timeout = 60
ifwi_release = utils.ReadConfig('IFWI_IMAGES', 'RELEASE')
logical_cores = int(utils.ReadConfig('1606827343', 'LOGICAL_CORES'))
max_active_thread = int(utils.ReadConfig('1606827343', 'MAX_ACTIVE_THREAD'))
soundwave_port = utils.ReadConfig('SOUNDWAVE', 'PORT')
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
    bios_conf.bios_control_key_press('ESC', 1, esc_timeout)
    is_efi = bios_conf.efi_shell_cmd("")
    if "Shell>" in is_efi:
        return "efi"
    elif "\\>" in is_efi:
        return "efi_fs"
    else:
        bios_conf.bios_control_key_press('ESC', 1, esc_timeout)
        result = bios_conf.bios_back_home(wait_time=esc_timeout)
        if result:
            return "bios"
        else:
            return "unknown"


def tear_down():
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


def flash_ifwi(image_for_flash, port='COM101',
               step_string="Flash the latest BIOS and boot to setup menu",
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


def itp_ctrl(status="open"):
    if status == "open":
        itp_sv.pythonsv_init()
        return True
    elif status == "close":
        itp_sv.pythonsv_exit()
        return True
    else:
        return False


def itp_msr(id, idx=0, step_string="reading itp.threads.msr MSR: ", complete=False):
    try:
        result = itp.threads[idx].msr(id)
        return result
    except Exception:
        result_process(False, "%s %s" % (step_string, id), test_exit=True, is_step_complete=complete)


def msr(id=None, step_string="reading MSR: ", complete=False):
    try:
        result = msr(id)
        return result
    except Exception:
        result_process(False, "%s %s" % (step_string, id), test_exit=True, is_step_complete=complete)


def bios_reset(flag=True, step_string="Save, reset, boot to BIOS", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        result = bios_conf.reset_to_bios(to_save=flag, wait_timeout=boot_wait_timeout, f2_press_wait=f2_timeout)
        result_process(result, step_string, test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def tme_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> "
                                        "Total Memory Encryption (TME): ",
            complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Memory Encryption (TME)', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def set_bypass(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> "
                                        "Total Memory Encryption (TME) Bypass: ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Total Memory Encryption (TME)Bypass', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def mktme_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> "
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
        result_process(result, "%s %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def mmio_high_base(value="16T",
                        step_string="EDKII -> Socket Configuration -> Uncore Configuration -> Uncore General Configuration -> MMIO High Base",
                        complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Uncore Configuration", "Uncore General Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('MMIO High Base', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value),
                       test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def check_msr_value(msr_val, sp):
    itp_ctrl("open")
    msr_core = itp_msr(id=msr_val, idx=0)
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_core)
    log_write("INFO", "MSR Info: thread 0 %s: %s, thread 0 binary converted: %s" % (
        msr_val, msr_core, r_bin))
    if sp == "step5":
        result = ["1" == r_bin[-1], "1" == r_bin[-2],
                  "0" == r_bin[-3], "1" == r_bin[-4],
                  "0000" == r_bin[-8:-4],
                  "1" in r_bin[-36:-32],
                  "1" == r_bin[-49], "1" == r_bin[50]]
        result_process(False not in result, "Check the value of IA32_TME_ACTIVATE MSR %s" % msr_val,
                       test_exit=True, is_step_complete=True)
    elif sp == "step6":
        result = ["1" == r_bin[-1]]
        result_process(False not in result, "Check the value of IA32_TME_ACTIVATE MSR %s" % msr_val,
                       test_exit=True, is_step_complete=True)
    elif sp == "step11":
        result = ["1" == r_bin[-1], "1" == r_bin[-2]]
        result_process(False not in result, "Check the value of IA32_TME_ACTIVATE MSR %s" % msr_val,
                       test_exit=True, is_step_complete=True)
    elif sp == "step12":
        result = ["1" == r_bin[-1], "1" == r_bin[-2],
                  "0" == r_bin[-3], "1" == r_bin[-4],
                  "0000" == r_bin[-8:-4],
                  "1" in r_bin[-32],
                  "0" in r_bin[-36:-32],
                  "1" == r_bin[-49], "0" == r_bin[50]]
        result_process(False not in result, "Check the value of IA32_TME_ACTIVATE MSR %s" % msr_val,
                       test_exit=True, is_step_complete=True)
    elif sp == "step13":
        result = msr_core != " " and msr_core != 0
        result_process(False not in result, "Check the value of IA32_TME_ACTIVATE MSR %s" % msr_val,
                       test_exit=True, is_step_complete=True)


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


@time_out(3600, callback_logging)
# Test Case Execution
def test_case_execution():
    # flash ifwi and boot to setup
    flash_ifwi(ifwi_release, complete=False)
    result = bios_init_opr()
    result_process(result, "Flash the latest BIOS and boot to setup menu", test_exit=True, is_step_complete=True)

    # step3:enable TME
    tme_set()

    # step4:set MMIO High base:16T
    mmio_high_base()

    # step5:Enable TME bypass and Disable MKTME,Check the value of IA32_TME_ACTIVATE MSR 0x982
    set_bypass()
    mktme_set()
    check_msr_value(msr_val="0x982", sp="step5")
    bios_reset(complete=False)

    # step6:Enable TME/TME bypass;Disable MKTME;Check the value of IA32_TME_ACTIVATE MSR 0x982
    mktme_set(value="Disable")
    check_msr_value(msr_val="0x982", sp="step12")
    check_msr_value(msr_val="0x992", sp="step13")
    check_msr_value(msr_val="0x993", sp="step13")
    bios_reset(complete=False)

    # step7:Disable TME;Enable TME bypass;Disable MKTME;Check the value of IA32_TME_ACTIVATE MSR 0x982
    tme_set(value="Disable")
    check_msr_value(msr_val="0x982", sp="step6")
    bios_reset(complete=False)

    # step8:Disable TME;Enable TME bypass;Enable MKTME;Check the value of IA32_TME_ACTIVATE MSR 0x982
    tme_set()
    mktme_set()
    tme_set(value="Disable")
    check_msr_value(msr_val="0x982", sp="step6")
    bios_reset(complete=False)

    # step9:Disable TME;Disable TME bypass;Enable MKTME;Check the value of IA32_TME_ACTIVATE MSR 0x982
    tme_set()
    set_bypass(value="Disable")
    tme_set(value="Disable")
    check_msr_value(msr_val="0x982", sp="step6")
    bios_reset(complete=False)

    # step10:Enable TME;Disable TME bypass;Enable MKTME;Check the value of IA32_TME_ACTIVATE MSR 0x982
    tme_set()
    check_msr_value(msr_val="0x982", sp="step5")
    bios_reset(complete=False)

    # step11:Enable TME;Disable TME bypass;Disable MKTME;Check the value of IA32_TME_ACTIVATE MSR 0x982
    mktme_set(value="Disable")
    check_msr_value(msr_val="0x982", sp="step11")
    bios_reset(complete=False)


if __name__ == "__main__":
    try:
        test_case_execution()
    except Exception:
        result_process(False, "Exception Occurred: \r\n %s" % (traceback.format_exc()), test_exit=True,
                       is_step_complete=True)
        sys.exit(1)
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
