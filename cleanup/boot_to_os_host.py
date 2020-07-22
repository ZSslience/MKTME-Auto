__author__ = r'jkmody\yusufmox\tnaidux'

# Global Python Imports
import sys

# Local Python Imports
import lib_constants
import library
import lib_boot_to_environment

# Global Variables
script_id = "boot_to_os_host.py"
test_case_id = "cleanup"
log_level = "ALL"
tbd = "None"
token = "OS"
token1 = "Boot to OS"
token = token.lower()

try:
    if lib_boot_to_environment.boot_to_os_setup(token1, test_case_id,
                                                script_id, log_level, tbd):
        library.write_log(lib_constants.LOG_PASS, "PASS: System booted to %s"
                          % token, test_case_id, script_id, "None", "None",
                          log_level, tbd)
        sys.exit(lib_constants.EXIT_SUCCESS)
    else:
        library.write_log(lib_constants.LOG_FAIL, "FAIL: Failed to boot to %s"
                          % token, test_case_id, script_id,
                          "None", "None", log_level, tbd)
        sys.exit(lib_constants.EXIT_FAILURE)
except Exception as e:
    library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                      test_case_id, script_id, "None", "None", log_level, tbd)
    sys.exit(lib_constants.EXIT_FAILURE)
