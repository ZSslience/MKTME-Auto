__author__ = 'yusufmox'

# Global Python Imports
import sys

# Local Python Imports
import library
import lib_constants
import cleanup

# Global Variables
log_level = "ALL"
tbd = "None"
tc_id = "cleanup"
script_id = "remote_reboot.py"

try:
    status = cleanup.remote_reboot(tc_id, script_id, log_level, tbd)

    if status:
        library.write_log(lib_constants.LOG_PASS, "PASS: Remote Reboot "
                          "performed successfully", tc_id, script_id,
                          "System_Cycling", "None", log_level, tbd)
        sys.exit(lib_constants.EXIT_SUCCESS)
    else:
        library.write_log(lib_constants.LOG_FAIL, "FAIL: Failed to perform "
                          "Remote Reboot", tc_id, script_id, "System_Cycling",
                          "None", log_level, tbd)
        sys.exit(lib_constants.EXIT_FAILURE)
except Exception as e:
    library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                      tc_id, script_id, "System_Cycling", "None", log_level,
                      tbd)
    sys.exit(lib_constants.EXIT_FAILURE)
