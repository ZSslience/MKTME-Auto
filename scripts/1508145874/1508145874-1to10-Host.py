import os
import sys
import time
import threading
import traceback
import pythonsv_icx_handler as itp_sv
from MiddleWare import lib_wmi_handler
from MiddleWare import lib_flash_server as lfs
from MiddleWare import lib_power_action_soundwave as lpa
from MiddleWare.lib_bios_config import BiosMenuConfig
from SoftwareAbstractionLayer import utils
from SoftwareAbstractionLayer import library
from SoftwareAbstractionLayer import lib_constants
from SoftwareAbstractionLayer import sal_remote_fetch
from SoftwareAbstractionLayer import sal_pstools

# 1508145874 [PSS  Post-Si][MKTME] System FW (BIOS) shall restore TME Key from last warm boot when ADR is enabled
# rev.10


# Constants Definition
TEST_CASE_ID = "1508145874"
SCRIPT_ID = "1508145874-1to10-Host.py"
IS_CASE_PASS = True
STEP_NO = 1
FAIL_COLLECT = []

# Variants Definition
opt_wait_time = 7
os_boot_timeout = 120
boot_wait_timeout = 600
f2_timeout = 20
sut_host = utils.ReadConfig('SUT_IP', 'target_sut_ip')
usb_drive_label = utils.ReadConfig('USB Drive', 'DRIVE_LETTER')
usb_drive_alias = utils.ReadConfig('USB Drive', 'EFI_ALIAS')
ifwi_release = utils.ReadConfig('IFWI_IMAGES', 'RELEASE')
logical_cores = int(utils.ReadConfig('1508145874', 'LOGICAL_CORES'))
max_active_thread = int(utils.ReadConfig('1508145874', 'MAX_ACTIVE_THREAD'))
phy_address_width = int(utils.ReadConfig('1508145874', 'PHYSICAL_ADDRESS_WIDTH'), 16)
msr_9ff_32_35 = utils.ReadConfig('1508145874', 'MSR_9FF_32_35')
soundwave_port = utils.ReadConfig('SOUNDWAVE', 'PORT')
wh = lib_wmi_handler.WmiHandler()
bios_conf = BiosMenuConfig(TEST_CASE_ID, SCRIPT_ID)

# Test Case Steps Abstraction


def result_process(result, step_string, test_exit=False, is_step_complete=True):
    global STEP_NO
    if not result:
        global IS_CASE_PASS
        IS_CASE_PASS = False
        if is_step_complete:
            library.write_log(lib_constants.LOG_FAIL, "Step %d: Failed to %s" % (STEP_NO, step_string),
                              TEST_CASE_ID, SCRIPT_ID)
            global FAIL_COLLECT
            FAIL_COLLECT.append((STEP_NO, step_string))
            STEP_NO += 1
        else:
            library.write_log(lib_constants.LOG_FAIL, "Failed to %s" % step_string,
                              TEST_CASE_ID, SCRIPT_ID)
        if test_exit:
            sys.exit(lib_constants.EXIT_FAILURE)
    else:
        if is_step_complete:
            library.write_log(lib_constants.LOG_INFO, "Step %d: Succeed to %s" % (STEP_NO, step_string),
                              TEST_CASE_ID, SCRIPT_ID)
            STEP_NO += 1
        else:
            library.write_log(lib_constants.LOG_INFO, "Succeed to %s" % step_string,
                              TEST_CASE_ID, SCRIPT_ID)


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


def tear_down():
    sut_state = is_boot_state()
    if sut_state == "windows":
        wh.wmi_os_opt(local=False, os_instruct="shutdown")
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


def reset_button():
    try:
        lpa.ac_off(soundwave_port)
        time.sleep(5)
        lpa.ac_on(soundwave_port)
        time.sleep(os_boot_timeout)
        return True
    except Exception:
        return False


def os_boot_check(round=1):
    for i in range(round):
        try:
            time.sleep(os_boot_timeout)
            result = wh.wmi_os_opt(local=False, os_instruct="name")
            log_write("INFO", "OS boot successfully.")
            return True
        except Exception:
            result = reset_button()
            if result:
                log_write("INFO", "OS reset triggered cycle %s" % i)
    return False


def test_flash_ifwi(image_for_flash, port='COM101', step_string="Flash the latest BIOS and boot to setup menu", complete=True):
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
        result_process(result, step_string, test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_reset(warm=False, step_string="System Reset: ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_back_home()
        if warm:
            bios_conf.enter_efi_shell(usb_drive_alias, 15)
            bios_conf.efi_shell_cmd('reset -w', 3)
        else:
            bios_conf.reset_system()
        result = bios_conf.enter_bios(boot_wait_timeout, f2_timeout)
        result_process(result, "%s: warm reset is %s" % (step_string, warm), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_max_mktme_keys_get(verdict="0x3f", step_string="EDKII -> Socket Configuration -> Processor Configuration -> Max MKTME keys: ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.get_system_information("Max MKTME Keys")
        result_process(verdict in result, "%s %s" % (step_string, result), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_aesni_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> AES-NI: ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('AES-NI', value)
        bios_conf.bios_save_changes()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_tme_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> Total Memory Encryption (TME): ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Total Memory Encryption (TME)', value)
        bios_conf.bios_save_changes()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_adr_set(value="Enable", step_string="EDKII -> Socket Configuration -> Memory Configuration -> Enable ADR: ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Memory Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Enable ADR', value)
        bios_conf.bios_save_changes()
        result_process(result, "%s %s" % (step_string, value), test_exit=False, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_fastboot_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> Attempt Fast Boot: ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Attempt Fast Boot', value)
        bios_conf.bios_save_changes()
        result_process(result, "%s %s" % (step_string, value), test_exit=False, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_mktme_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> Multi-Key Total Memory Encryption (MK-TME): ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Multikey Total Memory Encryption (MK-TME)', value)
        bios_conf.bios_save_changes()
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def disable_limit_pa46bits(value="Disable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> Limit CPU PA to 46 bits", complete=False):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Limit CPU PA to 46 bits', value)
        bios_conf.bios_save_changes()
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True,
                       is_step_complete=complete)


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
# Test Case Execution
def test_execution():
    # Test Run Start
    test_flash_ifwi(ifwi_release, complete=False)
    test_boot_to_setup(step_string="Flash the latest BIOS and boot to setup menu", complete=True)

    test_aesni_set(complete=False)
    test_tme_set(complete=False)
    test_mktme_set(complete=False)
    disable_limit_pa46bits(complete=False)
    test_reset(complete=True)

    itp_ctrl("open")
    msr_982_core_0 = test_itp_msr(id=0x982, idx=0)
    itp_ctrl("close")
    r_bin = "{0:64b}".format(msr_982_core_0)
    log_write("INFO", "MSR Info: thread 0 0x982: %s, thread 0 binary coverted: %s" % (msr_982_core_0, r_bin))
    # itp.threads[0].msr(0x982) same result withitp.threads[max_thread].msr(0x982)
    # The value of MSR.0x982 Bit[2] should be "0". The value of MSR.0x982 Bit[2] indicate:
    # 0 – Create a new TME key (expected cold/warm boot)
    # 1- Restore the TME key from storage(Expected when resume from standby)
    result = ["0" in r_bin[-3]]
    result_process(False not in result, "Check the value of TME/MK-TME ACTIVATE MSR 0x982. The value of MSR 0x982 Bit[2] should be 0")

    itp_ctrl("open")
    msr_992_core_0 = test_itp_msr(id=0x992, idx=0)
    msr_993_core_0 = test_itp_msr(id=0x993, idx=0)
    itp_ctrl("close")
    msr_992_bin = "{0:64b}".format(msr_992_core_0)
    msr_993_bin = "{0:64b}".format(msr_993_core_0)
    result_process(msr_992_bin and msr_993_bin, "MSR 0x992 Info: {}, MSR 0x993 Info: {}".format(msr_992_bin, msr_993_bin))

    test_adr_set(complete=False)
    test_fastboot_set(complete=False)
    test_reset(warm=True, complete=True)

    itp_ctrl("open")
    msr_992_core_0_b = test_itp_msr(id=0x992, idx=0)
    msr_993_core_0_b = test_itp_msr(id=0x993, idx=0)
    itp_ctrl("close")
    msr_992_bin_b = "{0:64b}".format(msr_992_core_0_b)
    msr_993_bin_b = "{0:64b}".format(msr_993_core_0_b)
    result = [(msr_992_bin == msr_992_bin_b), (msr_993_bin == msr_993_bin_b)]
    result_process(False not in result, "Check the value of MSR_TME_KEY_0 (0x992) and MSR_TME_KEY_1 (0x993) as same as step 4")

    itp_ctrl("open")
    msr_982_core_0 = test_itp_msr(id=0x982, idx=0)
    itp_ctrl("close")
    r_bin = "{0:64b}".format(msr_982_core_0)
    log_write("INFO", "MSR Info: thread 0 0x982: %s, thread 0 binary coverted: %s" % (msr_982_core_0, r_bin))
    # itp.threads[0].msr(0x982) same result withitp.threads[max_thread].msr(0x982)
    # The value of MSR.0x982 Bit[2] should be "0". The value of MSR.0x982 Bit[2] indicate:
    # 0 – Create a new TME key (expected cold/warm boot)
    # 1- Restore the TME key from storage(Expected when resume from standby)
    result = ["1" in r_bin[-3]]
    result_process(False not in result, "Check the value of TME/MK-TME ACTIVATE MSR 0x982. The value of MSR 0x982 Bit[2] should be 1")

    test_reset(complete=True)

    itp_ctrl("open")
    msr_992_core_0_b = test_itp_msr(id=0x992, idx=0)
    msr_993_core_0_b = test_itp_msr(id=0x993, idx=0)
    itp_ctrl("close")
    msr_992_bin_b = "{0:64b}".format(msr_992_core_0_b)
    msr_993_bin_b = "{0:64b}".format(msr_993_core_0_b)
    result = [(msr_992_bin != msr_992_bin_b), (msr_993_bin != msr_993_bin_b)]
    result_process(False not in result, "Check the value of MSR_TME_KEY_0 (0x992) and MSR_TME_KEY_1 (0x993) not same as step 4")

    itp_ctrl("open")
    msr_982_core_0 = test_itp_msr(id=0x982, idx=0)
    itp_ctrl("close")
    r_bin = "{0:64b}".format(msr_982_core_0)
    log_write("INFO", "MSR Info: thread 0 0x982: %s, thread 0 binary coverted: %s" % (msr_982_core_0, r_bin))
    # itp.threads[0].msr(0x982) same result withitp.threads[max_thread].msr(0x982)
    # The value of MSR.0x982 Bit[2] should be "0". The value of MSR.0x982 Bit[2] indicate:
    # 0 – Create a new TME key (expected cold/warm boot)
    # 1- Restore the TME key from storage(Expected when resume from standby)
    result = ["0" in r_bin[-3]]
    result_process(False not in result, "Check the value of TME/MK-TME ACTIVATE MSR 0x982. The value of MSR 0x982 Bit[2] should be 0")


if __name__ == "__main__":
    try:
        test_execution()
    except Exception:
        result_process(False, "Exception Occurred: \r\n %s" % (traceback.format_exc()), test_exit=True, is_step_complete=True)
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