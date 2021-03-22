import sys
import time
import threading
import traceback

from MiddleWare import lib_wmi_handler
from MiddleWare import lib_flash_server as lfs
from MiddleWare import lib_power_action_soundwave as lpa
from MiddleWare.lib_bios_config import BiosMenuConfig
from SoftwareAbstractionLayer import library
from SoftwareAbstractionLayer import lib_constants
from SoftwareAbstractionLayer import utils
import pythonsv_icx_handler as itp_sv

# Constants Definition
TEST_CASE_ID = "1508568416"
SCRIPT_ID = "1508568416-1to9-Host.py"
IS_CASE_PASS = True
STEP_NO = 1
FAIL_COLLECT = []

opt_wait_time = 60
os_boot_timeout = 120
boot_wait_timeout = 600
f2_timeout = 120
esc_timeout = 60
ifwi_release = utils.ReadConfig('IFWI_IMAGES', 'RELEASE')
# wh = lib_wmi_handler.WmiHandler()
soundwave_port = utils.ReadConfig('SOUNDWAVE', 'PORT')
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
    # try:
    #     result = wh.wmi_os_opt(local=False, os_instruct="name")
    #     if "Windows" in result[0]:
    #         return "windows"
    #     else:
    #         return "na"
    # except Exception:
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


def test_flash_ifwi(image_for_flash, port='COM101', step_string="Flash the latest BIOS and boot to setup menu",
                    complete=True):
    # os_state = is_boot_state()
    # if os_state == "windows":
    #     wh.wmi_os_opt(local=False, os_instruct="shutdown")
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
            # wh.wmi_os_opt(local=False, os_instruct="reboot")
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


def test_aesni_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> AES-NI: ",
                   complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('AES-NI', value)
        bios_conf.bios_save_changes()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True,
                       is_step_complete=complete)


def test_tme_set(value="Enable",
                 step_string="EDKII -> Socket Configuration -> Processor Configuration -> "
                             "Total Memory Encryption (TME): ",
                 complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Total Memory Encryption (TME)', value)
        bios_conf.bios_save_changes()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def disable_limit_pa46bits(value="Disable",
                           step_string="EDKII -> Socket Configuration -> Processor Configuration -> "
                                       "Limit CPU PA to 46 bits",
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
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_mktme_mem_integrity_set(value="Enable",
                                 step_string="EDKII -> Socket Configuration -> Processor Configuration -> "
                                             "Mktme memory integrity ",
                                 complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Mktme memory integrity', value)
        bios_conf.bios_save_changes()
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_mmio_high_base_set(value="16T", step_string="EDKII -> Socket Configuration -> "
                                                     "Common RefCode Configuration -> MMIO High Base",
                            complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Common RefCode Configuration"],
                                 wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select("MMIO High Base", value)
        bios_conf.bios_save_changes()
        bios_conf.bios_back_home()
        result_process(result, "%s:%s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state),
                       test_exit=True, is_step_complete=complete)


def test_bios_reset(flag=True, step_string="Save, reset, boot to BIOS", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        result = bios_conf.reset_to_bios(to_save=flag, wait_timeout=boot_wait_timeout, f2_press_wait=f2_timeout)
        result_process(result, step_string, test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True,
                       is_step_complete=complete)


def itp_ctrl(status="open"):
    if status == "open":
        itp_sv.pythonsv_init()
        return True
    elif status == "close":
        itp_sv.pythonsv_exit()
        return True
    else:
        return False


def test_itp_msr(id=0x982, idx=0, step_string="reading itp.threads.msr MSR: ", complete=False):
    try:
        result = itp.threads[idx].msr(id)
        return result
    except Exception:
        result_process(False, "%s %s" % (step_string, id), test_exit=True, is_step_complete=complete)


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


def callback_logging():
    result_process(False, "Test case execution terminated due to timeout occurred", test_exit=True,
                   is_step_complete=False)


@time_out(7200, callback_logging)
def test_execution():
    # Test Run Start
    # Step 1: Flash IFWI and boot to BIOS
    test_flash_ifwi(ifwi_release, complete=False)
    test_boot_to_setup(step_string="Flash the latest BIOS and boot to setup menu", complete=True)

    # Step 2: enable AES-NI
    # test_aesni_set() # Skip as it's enable by default

    # Step 3: enable TME
    test_tme_set()

    # Step 4: enable TME-MT
    # disable_limit_pa46bits(complete=False) # Skip as it's Disable by default on EGS Platform
    test_mktme_set(complete=False)
    test_mktme_mem_integrity_set(value="Disable")

    # Step 5: MMIO High Base configuration: 16T
    test_mmio_high_base_set()

    # Save configuration and reset
    test_bios_reset()

    # Step 6: Check MSR 0x981
    itp_ctrl("open")
    msr_981_core_0 = test_itp_msr(id=0x981, idx=0)
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_981_core_0)
    log_write("INFO", "MSR Info: thread 0 0x981: %s, binary repr: %s" % (msr_981_core_0, r_bin))
    result = ["1" == r_bin[-1],
              "1" == r_bin[-2],
              "1" in r_bin[-36:-32],
              "1" in r_bin[-51:-36]]
    result_process(False not in result, "Check the value of IA32_TME_CAPABILITY MSR 0x981", test_exit=True,
                   is_step_complete=True)

    # Step 7: Check MSR 0X982
    itp_ctrl("open")
    msr_982_core_0 = test_itp_msr(id=0x982, idx=0)
    itp_ctrl("close")
    r_bin = "{0:064b}".format(msr_982_core_0)
    log_write("INFO", "MSR Info: thread 0 0x982: %s, binary repr: %s" % (msr_982_core_0, r_bin))
    result = ["1" == r_bin[-1],
              "1" == r_bin[-2],
              "0" == r_bin[-3],
              "1" == r_bin[-4],
              "0000" == r_bin[-8:-4],
              "1" in r_bin[-36:-32],
              "1" == r_bin[-49],
              "0" == r_bin[-50]
              ]
    result_process(False not in result, "Check the value of IA32_TME_ACTIVATE MSR 0x982", test_exit=True,
                   is_step_complete=True)


def tear_down():
    sut_state = is_boot_state()
    # if sut_state == "windows":
    #     wh.wmi_os_opt(local=False, os_instruct="shutdown")
    log_write("INFO", "SUT is under %s state, perform G3" % sut_state)
    lpa.ac_off(soundwave_port)
    time.sleep(5)


if __name__ == '__main__':
    try:
        test_execution()
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
