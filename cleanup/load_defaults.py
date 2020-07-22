__author__ = 'yusufmox'

# Global Python Imports
import os
import subprocess
import sys

# Local Python Imports
import library
import lib_constants
import lib_load_bios_defaults
import cleanup
import pysvtools.xmlcli.XmlCli as cli

# Global Variables
log_level = "ALL"
tbd = "None"
tc_id = "cleanup"
script_id = "load_defaults.py"

try:
    if cleanup.clear_logical_drive():
        library.write_log(lib_constants.LOG_INFO, "Succeed to clean logical drive",
                          tc_id, script_id, "None", "None", log_level, tbd)
except Exception as e:
    library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                      tc_id, script_id, "None", "None", log_level, tbd)

try:
    cli.clb._setCliAccess("winsdk")
    cli.CvLoadDefaults()
    cli.clb.ConfXmlCli()

    library.write_log(lib_constants.LOG_PASS, "PASS: Bios Settings set to "
                      "defaults and XmlCli enabled", tc_id, script_id,
                      "XmlCli", "None", log_level, tbd)

    result_set_after_g3 = lib_load_bios_defaults.\
        set_state_after_g3("load_defaults", "load_defaults.py")

    if result_set_after_g3:
        library.write_log(lib_constants.LOG_PASS, "PASS: State After G3 set "
                          "to S5 State", tc_id, script_id, "XmlCli", "None",
                          log_level, tbd)
    else:
        library.write_log(lib_constants.LOG_FAIL, "FAIL: Failed to set State "
                          "After G3 to S5", tc_id, script_id, "XmlCli",
                          "None", log_level, tbd)
        sys.exit(lib_constants.EXIT_FAILURE)
except Exception as e:
    library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                      tc_id, script_id, "XmlCli", "None", log_level, tbd)
    sys.exit(lib_constants.EXIT_FAILURE)

try:
    os.system("powercfg -setacvalueindex SCHEME_CURRENT"
              " 4f971e89-eebd-4455-a8de-9e59040e7347"
              " 7648efa3-dd9c-4e3e-b566-50f929386280 0")

    os.system("powercfg -setdcvalueindex SCHEME_CURRENT"
              " 4f971e89-eebd-4455-a8de-9e59040e7347"
              " 7648efa3-dd9c-4e3e-b566-50f929386280 0")

    os.system("powercfg -change -hibernate-timeout-ac 0")
    os.system("powercfg -change -hibernate-timeout-dc 0")
    os.system("powercfg -change -standby-timeout-ac 0")
    os.system("powercfg -change -standby-timeout-dc 0")
    os.system("powercfg -change -monitor-timeout-ac 0")
    os.system("powercfg -change -monitor-timeout-dc 0")

    p = subprocess.Popen("powercfg -getactivescheme", shell=True,
                         stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    get_activeScheme = str(p.communicate()[0])

    get_arr = get_activeScheme.split(":")[1]
    active_scheme = get_arr.split(" ")[1].strip()

    os.system("powercfg -SETACVALUEINDEX " + active_scheme +
              " SUB_NONE CONSOLELOCK 0")
    os.system("powercfg -SETDCVALUEINDEX " + active_scheme +
              " SUB_NONE CONSOLELOCK 0")
    os.system("powercfg -SetActive SCHEME_CURRENT")

    library.write_log(lib_constants.LOG_PASS, "PASS: Power Settings set to "
                      "defaults", tc_id, script_id, "None", "None", log_level,
                      tbd)
except Exception as e:
    library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                      tc_id, script_id, "None", "None", log_level, tbd)
    sys.exit(lib_constants.EXIT_FAILURE)

os.system("del /q /f /s %TEMP%\*")
library.write_log(lib_constants.LOG_PASS, "PASS: Load Defaults action "
                  "completed successfully and All Temporary Files are deleted "
                  "from temp folder", tc_id, script_id, "None", "None",
                  log_level, tbd)
sys.exit(lib_constants.EXIT_SUCCESS)
