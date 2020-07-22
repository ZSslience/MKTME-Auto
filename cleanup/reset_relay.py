__author__ = r'yusufmox\tnaidux'

# Global Python Imports
import os
import sys

# Local Python Imports
import lib_constants
import library
import cleanup
if os.path.exists(lib_constants.TTK2_INSTALL_FOLDER):
    import lib_ttk2_operations

# Global Variables
log_level = "ALL"
tbd = "None"
tc_id = "cleanup"
script_id = "reset_relay.py"

try:
    ac_switch_status = lib_ttk2_operations.\
        get_ttk2_ac_switch_status(lib_constants.TTK2_SWITCH_NO_AC, tc_id,
                                  script_id, log_level, tbd)

    if ac_switch_status is False:
        lib_ttk2_operations.ac_on_off("ON", lib_constants.TTK2_SWITCH_NO_AC,
                                      tc_id, script_id, log_level, tbd)

    status = lib_ttk2_operations.ttk2_reset_relay("OFF", "None", "None",
                                                  log_level, tbd)               # Function call to reset all the relay

    if status:
        library.write_log(lib_constants.LOG_PASS, "PASS: Relay Reset performed"
                          " successfully", tc_id, script_id, "TTK2", "None",
                          log_level, tbd)
        cleanup.kill_ttk2()
    else:
        library.write_log(lib_constants.LOG_FAIL, "FAIL: Failed to perform "
                          "Relay Reset operation", tc_id, script_id, "TTK2",
                          "None", log_level, tbd)
    cleanup.kill_ttk2()
except Exception as e:
    library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                      tc_id, script_id, "TTK2", "None", log_level, tbd)
    sys.exit(lib_constants.EXIT_FAILURE)
