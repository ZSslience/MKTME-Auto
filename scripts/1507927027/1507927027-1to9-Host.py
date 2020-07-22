import os
import re
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
from SoftwareAbstractionLayer import sal_remote_fetch
from SoftwareAbstractionLayer import sal_pstools

# 1507927027 [PSS  Post-Si][MKTME] TME_MKTME and AppDirect can not be existed mutually
# rev.18

# Constants Definition
TEST_CASE_ID = "1507927027"
SCRIPT_ID = "1507927027-1to9-Host.py"
IS_CASE_PASS = True
STEP_NO = 1
FAIL_COLLECT = []

# Variants Definition
opt_wait_time = 8
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


def reset_button(timeout=os_boot_timeout):
    try:
        lpa.ac_off(soundwave_port)
        time.sleep(5)
        lpa.ac_on(soundwave_port)
        time.sleep(timeout)
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


def test_reset_to_efi(flag=True, step_string="Save, reset, boot to EFI Shell", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        result = bios_conf.reset_to_bios(to_save=flag, wait_timeout=boot_wait_timeout, f2_press_wait=f2_timeout)
        result_process(result, "Save, reset, boot to BIOS", test_exit=True, is_step_complete=False)
        fs_drive = bios_conf.enter_efi_shell(volume_alias=usb_drive_alias)
        return fs_drive
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_max_mktme_keys_get(verdict="0x3F", step_string="EDKII -> Socket Configuration -> Processor Configuration -> Max MKTME keys: ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.get_system_information("Max MKTME Keys")
        result_process(verdict in result, "%s %s" % (step_string, result), test_exit=True, is_step_complete=complete)
        return result
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)
        return False


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
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_mktme_set(value="Enable", step_string="EDKII -> Socket Configuration -> Processor Configuration -> Multi-Key Total Memory Encryption (MK-TME): ", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Multikey Total Memory Encryption (MK-TME)', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_dimm_mngment(value="BIOS Setup", step_string="EDKII -> Socket Configuration -> Memory Configuration -> Memory Dfx Configuration -> DIMM Management", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Memory Configuration", "Memory Dfx Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('DIMM Management', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s: %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_mem_app_direct(value="Disable", step_string="EDKII -> Socket Configuration -> Memory Configuration -> Memory Dfx Configuration -> AppDirect", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Memory Configuration", "Memory Dfx Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('AppDirect', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s: %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_tme_addr_set(value="1000", step_string="Providing our own address to be exclude from the encrypting through MKTME", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration", "Processor Dfx Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_textbox_input('TME Exclusion Base Address Increment Value', value)
        result = bios_conf.bios_opt_textbox_input('TME Exclusion Length Increment value', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s: %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_crdimm_prov(value="create", step_string="Provision CR DIMMs as AppDirect Mode", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        if value == 'create':
            result = bios_conf.bios_menu_navi(["EDKII Menu", "Intel(R) Optane(TM) Persistent Memory Configuration", "Provisioning", "Create goal config", "Create goal config"], wait_time=opt_wait_time)
        elif value == 'delete':
            result = bios_conf.bios_menu_navi(["EDKII Menu", "Intel(R) Optane(TM) Persistent Memory Configuration", "Provisioning", "Delete goal config", "Delete goal config"], wait_time=opt_wait_time)
        time.sleep(2)
        bios_conf.bios_back_home()
        result_process(result, "%s: %s" % (value, step_string), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_volatile_mem_mode(value="1LM", step_string="Set CR DIMMs in the 1LM mode", complete=True):
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Memory Configuration", "Memory Map"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Volatile Memory Mode', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s: %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_serial_debug_msg_lvl(value="Maximum", step_string="EDKII Menu ->Platform Configuration->Miscellaneous Configuration->Serial Debug Message Level -> Maximum / Normal", complete=True):
    # Disable/ Minimum/ Normal/ Maxium/ Auto/ Fixed PCD
    boot_state = is_boot_state()
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Platform Configuration", "Miscellaneous Configuration"], wait_time=opt_wait_time)
        result = bios_conf.bios_opt_drop_down_menu_select('Serial Debug Message Level', value)
        bios_conf.bios_save_changes()
        time.sleep(5)
        bios_conf.bios_back_home()
        result_process(result, "%s %s" % (step_string, value), test_exit=True, is_step_complete=complete)
    else:
        result_process(False, "%s: SUT is under %s" % (step_string, boot_state), test_exit=True, is_step_complete=complete)


def test_efi_command_run(command, wait_time, step_string, complete=True, log=False):
    reset_button(1)
    bios_conf.enter_bios(wait_timeout=boot_wait_timeout, f2_timeout=f2_timeout)
    fs_drive = bios_conf.enter_efi_shell(volume_alias=usb_drive_alias, time_out=30)
    print(fs_drive)
    bios_conf.efi_shell_cmd(fs_drive)
    if log:
        log_file_info = TEST_CASE_ID + "_Step_" + str(STEP_NO) + ".log"
        print(log_file_info)
        result = bios_conf.efi_shell_cmd(command + " > " + log_file_info, wait_time)
        result_process(result, step_string, test_exit=True, is_step_complete=complete)
        return log_file_info
    else:
        result = bios_conf.efi_shell_cmd(command, wait_time)
        result_process(result, step_string, test_exit=True, is_step_complete=complete)
        print(result)
        return result


def test_check_tme_entry(operate=False):
    reset_button(1)
    bios_conf.enter_bios(wait_timeout=boot_wait_timeout, f2_timeout=f2_timeout)
    boot_state = is_boot_state()
    result_string = []
    if boot_state == 'bios':
        bios_conf.bios_menu_navi(["EDKII Menu", "Socket Configuration", "Processor Configuration"], wait_time=opt_wait_time)
        result = bios_conf.get_system_information('Multikey Total Memory Encryption (MK-TME)')
        if result:
            result_string.append("Multikey Total Memory Encryption (MK-TME): %s" % result)
        else:
            result_string.append("Multikey Total Memory Encryption (MK-TME): not appear")

        result = bios_conf.get_system_information('Max MKTME Keys')
        if result:
            result_string.append("Max MKTME Keys: %s" % result)
        else:
            result_string.append("Max MKTME Keys: not appear")

        bios_conf.bios_menu_navi(["Processor Dfx Configuration"], wait_time=opt_wait_time)

        result = bios_conf.get_system_information('TME Exclusion Base Address Increment Value')
        if result:
            if operate:
                result = bios_conf.bios_opt_textbox_input('TME Exclusion Base Address Increment Value', "1000")
                result_string.append("TME Exclusion Base Address Increment Value: operate")
            else:
                result_string.append("TME Exclusion Base Address Increment Value: %s" % result)
        else:
            result_string.append("TME Exclusion Base Address Increment Value: not appear")

        result = bios_conf.get_system_information('TME Exclusion Length Increment value')
        if result:
            result_string.append("TME Exclusion Length Increment value: %s" % result)
            if operate:
                result = bios_conf.bios_opt_textbox_input('TME Exclusion Length Increment value', "0")
                result_string.append("TME Exclusion Length Increment value: operate")
        else:
            result_string.append("TME Exclusion Length Increment value: not appear")
        return(result_string)


def test_memmap_parse(log_file, query_string):
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding="utf_16_le") as buf:
            map_data = buf.read()
        data = map_data.split('\n')
        search_string = r'(.*) (.*)-(.*) (.*) (.*)'
        ret_list = list(filter(lambda x: re.match(search_string, x) is not None, data))
        ret_index = [ret_list.index(i) for i in ret_list if "8000F" in i]
        return ret_index[-1], len(ret_list), ret_list


def test_boot_dimm_table_parse(buffer):
    if type(buffer) == bytes:
        buffer = buffer.decode('ISO-8859-1').split('\r\n')
    dimminfo_table_range = [buffer.index(i) for i in buffer if "DIMMINFO_TABLE" in i]
    dimminfo_table = buffer[dimminfo_table_range[0]:dimminfo_table_range[1]]
    print(dimminfo_table)
    sad_table_start_range = [buffer.index(i) for i in buffer if "SAD table" in i]
    sad_table_end_range = [buffer.index(i) for i in buffer if "</SADTable>" in i]
    sad_table = buffer[sad_table_start_range[0]:sad_table_end_range[0]]
    print(sad_table)
    return dimminfo_table, sad_table


def test_capture_debug_log(capture=True, complete=True, log_file=None):
    if capture:
        hs._imp_port_mngr("open")
        result_process(True, "Perform Capture of debug log", test_exit=True, is_step_complete=complete)
    else:
        result_process(True, "Perform Stop Capture of debug log", test_exit=True, is_step_complete=complete)
        synced_serial = hs._imp_buffer_sync()
        print(log_file)
        if log_file:
            print("Saving to file")
            with open(log_file, 'wb') as buf:
                buf.write(synced_serial)
                buf.flush()
                buf.close()
        return synced_serial


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
    test_boot_to_setup(step_string="Flash the latest BIOS and boot to setup menu")

    test_aesni_set(complete=False)
    test_tme_set(complete=False)
    test_mktme_set(complete=False)
    result_process(True, "Enable TME and MKTME by traveling the follow knobs", test_exit=True, is_step_complete=True)

    test_volatile_mem_mode(value="1LM", complete=False)
    test_crdimm_prov(value="create", step_string="Enable CRDIMM AppDirect Mode Provisioning as TME/MK-TME Enabled", complete=True)
    bios_conf.bios_control_key_press('CTRL_ALT_DELETE', times=1, time_out=1)
    result_process(True, "Reboot the system")
    test_capture_debug_log(complete=False)
    bios_conf.enter_bios(boot_wait_timeout, f2_timeout)
    tme_en_appdirect_buffer = test_capture_debug_log(complete=False, capture=False, log_file='%s_%s.log' % (TEST_CASE_ID, STEP_NO))
    boot_dimminfo_table, boot_sad_table = test_boot_dimm_table_parse(tme_en_appdirect_buffer)
    result_dimm = len([i for i in boot_dimminfo_table if "DIMM: Intel" in i])
    result_sad = len([i for i in boot_sad_table if "PMEM" in i])
    result_process((result_dimm > 0) and (result_sad == 0), "TME/MK-TME Enabled: CR dimms are installed in DIMMINFO Table and PMem not listed in SAD Table", test_exit=True, is_step_complete=True)

    test_mktme_set(value="Disable", complete=False)
    test_tme_set(value="Disable", complete=False)
    bios_conf.bios_initialize(boot_wait_timeout, f2_timeout)
    # test_crdimm_prov(value="delete", step_string="Remove CRDIMM AppDirect Mode Provisioning", complete=False)
    test_crdimm_prov(value="create", step_string="Enable CRDIMM AppDirect Mode Provisioning as TME/MK-TME Disabled", complete=True)
    bios_conf.bios_control_key_press('CTRL_ALT_DELETE', times=1, time_out=1)
    test_capture_debug_log(complete=False)
    bios_conf.enter_bios(boot_wait_timeout, f2_timeout)
    tme_dis_appdirect_buffer = test_capture_debug_log(complete=False, capture=False, log_file='%s_%s.log' % (TEST_CASE_ID, STEP_NO))
    boot_dimminfo_table, boot_sad_table = test_boot_dimm_table_parse(tme_dis_appdirect_buffer)
    result_dimm = len([i for i in boot_dimminfo_table if "DIMM: Intel" in i])
    result_sad = len([i for i in boot_sad_table if "PMEM" in i])
    result_process((result_sad != 0), "TME/MK-TME Disabled: CR dimms are PMem not listed in SAD Table", test_exit=True, is_step_complete=True)

    test_tme_set(complete=False)
    test_mktme_set(complete=False)
    bios_conf.bios_control_key_press('CTRL_ALT_DELETE', times=1, time_out=1)
    result_process(True, "Reboot the system")
    test_capture_debug_log(complete=False)
    bios_conf.enter_bios(boot_wait_timeout, f2_timeout)
    tme_en_cr_check_buffer = test_capture_debug_log(complete=False, capture=False, log_file='%s_%s.log' % (TEST_CASE_ID, STEP_NO))
    boot_dimminfo_table, boot_sad_table = test_boot_dimm_table_parse(tme_en_cr_check_buffer)
    result_dimm = len([i for i in boot_dimminfo_table if "DIMM: Intel" in i])
    result_sad = len([i for i in boot_sad_table if "PMEM" in i])
    result_process((result_dimm > 0) and (result_sad == 0), "TME/MK-TME Re-Enabled: CR dimms are installed in DIMMINFO Table and PMem not listed in SAD Table", test_exit=True, is_step_complete=True)


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