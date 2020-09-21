import sys
import time
import threading
import traceback
import pythonsv_icx_handler as itp_sv
from HardwareAbstractionLayer import hal_serial_opt as hso
from MiddleWare import lib_wmi_handler
from MiddleWare import lib_flash_server as lfs
from MiddleWare import lib_power_action_soundwave as lpa
from MiddleWare.lib_bios_config import BiosMenuConfig
from SoftwareAbstractionLayer import utils
from SoftwareAbstractionLayer import library
from SoftwareAbstractionLayer import lib_constants


# 1606806788 [Pre-Si & PostS-i]No MKTME Error Code should be displayed in the BIOS Logs for boot without MKTME BIOS flow error cases.
# rev.15

# Constants Definition
TEST_CASE_ID = "1606806788"
SCRIPT_ID = "1606806788-1to6-Host.py"
IS_CASE_PASS = True
STEP_NO = 1
FAIL_COLLECT = []

# Variants Definition
opt_wait_time = 5
os_boot_timeout = 120
boot_wait_timeout = 600
f2_timeout = 20
sut_host = utils.ReadConfig('SUT_IP', 'target_sut_ip')
usb_drive_label = utils.ReadConfig('USB Drive', 'DRIVE_LETTER')
usb_drive_alias = utils.ReadConfig('USB Drive', 'EFI_ALIAS')
ifwi_release = utils.ReadConfig('IFWI_IMAGES', 'RELEASE')
soundwave_port = utils.ReadConfig('SOUNDWAVE', 'PORT')
wh = lib_wmi_handler.WmiHandler()
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


def test_get_gv_state(initial_step=False):
    itp, sv = itp_sv.pythonsv_init()
    result_process(True, "Initialize ITP environment.", test_exit=True, is_step_complete=initial_step)
    itp.unlock()
    itp.forcereconfig()
    sv.refresh()
    tme_active = sv.socket0.uncore.memss.mc0.ch0.tme.tme_activate.show()
    print(tme_active)
    max_ratio = sv.socket0.pcudata.global_max_ratio_2
    grtee_ratio = sv.socket0.pcudata.global_guaranteed_ratio_2
    effect_ratio = sv.socket0.pcudata.global_max_efficiency_ratio_2
    itp_sv.pythonsv_exit()
    return max_ratio, grtee_ratio, effect_ratio

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


def test_max_mktme_keys_get(verdict="0x3f", step_string="EDKII -> Socket Configuration -> Processor Configuration -> Max TME-MT Keys: ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.get_system_information("Max TME-MT Keys")
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


def test_mktme_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> Total Memory Encryption Multi-Tenant(TME-MT): ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Total Memory Encryption Multi-Tenant(TME-MT)', value)
        bios_conf.bios_save_changes()
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_serial_debug_msg_lvl(value="Maximum", step_string="EDKII Menu ->Platform Configuration->Miscellaneous Configuration->Serial Debug Message Level -> Maximum / Normal", complete=True):
    # Disable/ Minimum/ Normal/ Maxium/ Auto/ Fixed PCD
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Platform Configuration", "Miscellaneous Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Serial Debug Message Level', value)
        bios_conf.bios_save_changes()
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_capture_debug_log(capture=True, complete=True):
    if capture:
        hs._imp_port_mngr("open")
        result_process(True, "Perform Capture of debug log", test_exit=True, is_step_complete=complete)
    else:
        result_process(True, "Perform Stop Capture of debug log", test_exit=True, is_step_complete=complete)
        return hs._imp_buffer_sync()


def test_bios_boot_log_cap(step_string="Start collecting the serial Logs", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.reset_system()
        test_capture_debug_log(complete=False)
        bios_conf.enter_bios(2*boot_wait_timeout, f2_timeout)
        cap = test_capture_debug_log(capture=False, complete=True)
        result_process(True, step_string, test_exit=True, is_step_complete=complete)
        return cap
    result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_serial_log_check(buffer, query):
    if type(buffer) == bytes:
        buffer = buffer.decode('ISO-8859-1').split('\r\n')
    matched_list = [_ for _ in buffer if query in _]
    return matched_list


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


@time_out(3600, callback_logging)
# Test Case Execution
def test_execution():
    # Test Run Start
    test_flash_ifwi(ifwi_release, complete=False)
    test_boot_to_setup(step_string="Flash the latest BIOS and boot to setup menu", complete=True)

    test_aesni_set(complete=False)
    test_tme_set(complete=False)
    disable_limit_pa46bits()
    test_mktme_set(step_string="AES-NI, TME, MKTME Enabled and Save", complete=True)
    test_serial_debug_msg_lvl(value="Normal", complete=True)
    result = test_bios_boot_log_cap()

    result = test_serial_log_check(result, "Major Warning Code")
    ret_major_warn_code = []
    ret_minor_warn_code = []
    for i in result:
        ret_major_warn_code.append(i.split(",")[0].split(" = ")[-1])
        ret_minor_warn_code.append(i.split(",")[1].split(" = ")[-1])
    ret_major_warn_code = list(dict.fromkeys(ret_major_warn_code))
    ret_minor_warn_code = list(dict.fromkeys(ret_minor_warn_code))
    major_warning_code = utils.ReadConfig('1606806788', 'MAJOR_WARNING_CODE')
    minor_warning_code = utils.ReadConfig('1606806788', 'MINOR_WARNING_CODE')
    major_warning_code = major_warning_code.split(", ")
    minor_warning_code = minor_warning_code.split(", ")
    print(ret_major_warn_code, major_warning_code)
    result = [_ for _ in ret_major_warn_code if _ in major_warning_code]
    result_process(len(result) == 0, "Not Major Warning Code observed in serial log", test_exit=False, is_step_complete=True)
    print(ret_minor_warn_code, minor_warning_code)
    result = [_ for _ in ret_minor_warn_code if _ in minor_warning_code]
    result_process(result, "Minor Warning Code printed in serial log" , test_exit=False, is_step_complete=True)


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