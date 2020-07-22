__author__ = r'yusufmox\tnaidux\jpuklatx'

# Global Python Imports
import mmap
import os
import subprocess
import time

# Local Python Imports
import library
import lib_constants
import utils
if os.path.exists(lib_constants.TTK2_INSTALL_FOLDER):
    import lib_ttk2_operations
if os.path.exists(lib_constants.CSWITCH_INSTALLED_PATH):
    import lib_cswitch

# Global Variables
postcode_list = ["10ac", "10ad", "00ad", "00ac", "10ab"]
os_post_code_list = ["0000", "ab03", "ab04", "abc5"]

################################################################################
# Function Name : read_config
# Parameters    : tag, value
# Functionality : Reads config variables
# Return Value  : None
################################################################################


def read_config(tag, value):
    return utils.ReadConfig(tag, value)

################################################################################
# Function Name : checkcuros()
# Parameters    : None
# Return Value  : Returns the current system state (OS, EDK Shell, BIOS Setup)
# Functionality : check for current system state
################################################################################


def checkcuros(test_case_id, script_id, log_level="ALL", tbd=None):

    try:
        sut_ip = read_config("SUT_IP", "IP")                                    # Reading IP from the config file section SUT_IP

        if "FAIL" in sut_ip:
            library.write_log(lib_constants.LOG_WARNING, "WARNING: Failed to "
                              "get the config entry IP under [SUT_IP]",
                              test_case_id, script_id, "None", "None",
                              log_level, tbd)
            return False
        else:
            library.write_log(lib_constants.LOG_INFO, "INFO: config entry "
                              "IP under [SUT_IP] fetched", test_case_id,
                              script_id, "None", "None", log_level, tbd)

        os.chdir(os.getcwd())
        os.system("ping " + sut_ip + " > Result.txt")                           # Writing the ping status in result.txt file

        flag = 0
        with open('Result.txt', 'r') as file:                                   # Open Result.txt in read mode
            for line in file:
                if 'Destination host unreachable.' in line:
                    flag = 1
                    break
                elif 'could not find' in line:
                    flag = 1
                    break
                elif 'Request timed out.' in line:
                    flag = 1
                    break

        if flag == 1:                                                           # If flag ==1 system is either in edk shell or bios
            with open("Verify.txt", "w") as file:                               # Open Verify.txt in write mode
                file.write("SUT is in EDK")
                file.close()
                library.write_log(lib_constants.LOG_INFO, "INFO: System "
                                  "current state is either EDK or BIOS",
                                  test_case_id, script_id, "None", "None",
                                  log_level, tbd)
                return "EDK SHELL"                                              # Return "EDK shell" as system state if ping fails
        else:
            result, current_post_code = lib_ttk2_operations.\
                check_for_post_code(os_post_code_list, lib_constants.TWO_MIN,
                                    test_case_id, script_id, log_level, tbd)
            if current_post_code not in postcode_list and \
               current_post_code in os_post_code_list and result:
                library.write_log(lib_constants.LOG_INFO, "INFO: Ping operation"
                                  " successful to target machine %s" % sut_ip,
                                  test_case_id, script_id, "None", "None",
                                  log_level, tbd)

                library.write_log(lib_constants.LOG_INFO, "INFO: System "
                                  "current state is OS", test_case_id,
                                  script_id, "None", "None", log_level, tbd)

                with open("Verify.txt", "w") as file:                           # Open Verify.txt in write mode
                    file.write("SUT is in OS")
                    file.close()
                return "OS"                                                     # Return "OS" as system state if ping pass
    except Exception as e:
        library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                          test_case_id, script_id, "None", "None", log_level,
                          tbd)
        return False

################################################################################
# Function Name : change_bootorder_in_edkshell()
# Parameters    : test_case_id, script_id, log_level, tbd
# Return Value  : Sets EDKas first boot order. Triggered from host
# Functionality : Changes boot order from edk shell
################################################################################


def change_bootorder_in_edkshell(test_case_id, script_id, log_level="ALL",
                                 tbd=None):                                     # Boot order change in EDK shell

    try:
        port = read_config("BRAINBOX", "PORT")                                  # Read config file for sending keys from section Brainbox
        k1 = library.KBClass(port)                                              # Calls KB class for keypress

        time.sleep(lib_constants.SEND_KEY_TIME)
        k1.sendWithEnter("bcfg boot mv 1 0")                                    # Sending keyboard command to change boot order command

        time.sleep(lib_constants.SEND_KEY_TIME)
        k1.sendWithEnter("reset")                                               # Sending keyboard commands to reset

        time.sleep(lib_constants.LONG_TIME)

        library.write_log(lib_constants.LOG_INFO, "INFO: Keys sent from "
                          "brainbox to change boot order in EDK successfully",
                          test_case_id, script_id, "None", "None", log_level,
                          tbd)
        return True
    except Exception as e:
        library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                          test_case_id, script_id, "None", "None", log_level,
                          tbd)
        return False

################################################################################
# Function Name : remote_reboot
# Parameters    : test_case_id, script_id, log_level, tbd
# Return Value  : Returns True on successful restart action, False otherwise
# Purpose       : To perform restart on target machine
################################################################################


def remote_reboot(test_case_id, script_id, log_level="ALL", tbd=None):

    try:
        sx_state = "WR"
        cycles = 1
        duration = 30

        system_cycling_tool_path = read_config("System_Cycling_Tool",
                                               "tool_path")
        system_cycling_exe = read_config("System_Cycling_Tool",
                                         "system_cycling_exe")
        target_sut_ip = read_config("SUT_IP", "target_sut_ip")

        if "FAIL:" in [system_cycling_tool_path, system_cycling_exe,
                       target_sut_ip]:
            library.write_log(lib_constants.LOG_WARNING, "WARNING: Failed to "
                              "get the required config entries", test_case_id,
                              script_id, "None", "None", log_level, tbd)
            return False

        command = '"' + str(system_cycling_exe).strip() + '"' + ' -al -ip ' + \
            str(target_sut_ip) + ' -' + str(sx_state) + ' i:' + str(cycles) + \
            ' tw:' + str(duration) + ' ts:' + str(30)                           # Command to execute Warm Reset using Intel System Cycling Tool

        library.write_log(lib_constants.LOG_INFO, "INFO: Command to Perform "
                          "remote reboot is %s " % command, test_case_id,
                          script_id, "None", "None", log_level, tbd)

        if os.path.exists(system_cycling_tool_path):
            library.write_log(lib_constants.LOG_INFO, "INFO: System Cycling "
                              "tool path exists in the system", test_case_id,
                              script_id, "None", "None", log_level, tbd)
            os.chdir(system_cycling_tool_path)

            library.write_log(lib_constants.LOG_INFO, "INFO: Changed current "
                              "directory path to System Cycling Tool path ",
                              test_case_id, script_id, "None", "None",
                              log_level, tbd)
        else:
            library.write_log(lib_constants.LOG_WARNING, "WARNING: System "
                              "Cycling Tool does not exist", test_case_id,
                              script_id, "None", "None", log_level, tbd)
            return False

        result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                  stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.communicate()[0]
        returncode = int(result.returncode)

        os.system("ping " + target_sut_ip + " > Result.txt")                    # Writing the ping status in result.txt file

        flag = 0
        with open("Result.txt", "r") as file_out:                               # Open Result.txt in read mode
            for line in file_out:
                if "destination host unreachable." in line.lower():
                    flag = 1
                    break
                elif "could not find" in line.lower():
                    flag = 1
                    break
                elif "Request timed out." in line.lower():
                    flag = 1
                    break

        if 1 == flag:
            library.write_log(lib_constants.LOG_INFO, "INFO: System is "
                              "BIOS or EDK Shell", test_case_id, script_id,
                              "None", "None", log_level, tbd)
            return False
        else:
            if 1 != flag and 0 == returncode or 5 == returncode:
                library.write_log(lib_constants.LOG_INFO, "INFO: Ping "
                                  "operation to target System is successful",
                                  test_case_id, script_id, "None", "None",
                                  log_level, tbd)

                library.write_log(lib_constants.LOG_INFO, "INFO: System is "
                                  "in OS", test_case_id, script_id, "None",
                                  "None", log_level, tbd)
                return True
            else:
                library.write_log(lib_constants.LOG_INFO, "INFO: Failed to "
                                  "perform Ping operation to target System, "
                                  "SUT is not in OS", test_case_id, script_id,
                                  "None", "None",
                                  log_level, tbd)

                library.write_log(lib_constants.LOG_WARNING, "WARNING: Failed "
                                  "to perform Remote Reboot operation",
                                  test_case_id, script_id, "None", "None",
                                  log_level, tbd)
                return False
    except Exception as e:
        library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                          test_case_id, script_id, "None", "None", log_level,
                          tbd)
        return False

################################################################################
# Function Name : monitor_service_up
# Parameters    : test_case_id, script_id, log_level, tbd
# Return Value  : Returns True if SUT is in OS else False
# Purpose       : To Check sut is in OS
################################################################################


def monitor_service_up(test_case_id, script_id, log_level="ALL", tbd=None):

    try:
        post_code = ["0000", "ab03", "ab04", "abc5"]
        if library.check_for_post_code(post_code, 250, test_case_id, script_id,
                                       log_level, tbd):                         # If post code found, pass

            library.write_log(lib_constants.LOG_INFO, "INFO: Post code read "
                              "successfully for OS", test_case_id, script_id,
                              "None", "None", log_level, tbd)

            target_sut_ip = read_config("SUT_IP", "IP")

            if "FAIL:" in target_sut_ip:
                library.write_log(lib_constants.LOG_WARNING, "WARNING: Failed "
                                  "to get config entries under tag [SUT_IP] "
                                  "for IP", test_case_id, script_id, "None",
                                  "None", log_level, tbd)
                return False

            time.sleep(60)
            os.chdir(os.getcwd())
            os.system("ping " + target_sut_ip + " > Result.txt")                # Writing the ping status in result.txt file

            flag = 0
            with open("Result.txt", "r") as file_out:                           # Open Result.txt in read mode
                for line in file_out:
                    if "destination host unreachable." in line.lower():
                        flag = 1
                        break
                    elif "could not find" in line.lower():
                        flag = 1
                        break
                    elif "Request timed out." in line.lower():
                        flag = 1
                        break

            if 1 == flag:
                library.write_log(lib_constants.LOG_WARNING, "WARNING: Failed "
                                  "to ping to target SUT", test_case_id,
                                  script_id, "None", "None", log_level, tbd)
                return False
            else:
                library.write_log(lib_constants.LOG_INFO, "INFO: Successfully "
                                  "pinged SUT and SUT is in OS", test_case_id,
                                  script_id, "None", "None", log_level, tbd)
                return True
        library.write_log(lib_constants.LOG_WARNING, "WARNING: Failed to read "
                          "desired post code for OS", test_case_id, script_id,
                          "None", "None", log_level, tbd)
        return False
    except Exception as e:
        library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                          test_case_id, script_id, "None", "None", log_level,
                          tbd)
        return False

################################################################################
# Function Name : monitor_service_down
# Parameters    : test_case_id, script_id, log_level, tbd
# Return Value  : Returns True if SUT is in shutdown state else False
# Purpose       : To Check sut is in Shutdown state
################################################################################


def monitor_service_down(test_case_id, script_id, log_level="ALL", tbd=None):

    try:
        post_code = ["b505", "FFFF"]
        if library.check_for_post_code(post_code, 600, test_case_id, script_id,
                                       log_level, tbd):                         # If post code found, pass

            library.write_log(lib_constants.LOG_INFO, "INFO: Post code read"
                              " successfully for S5", test_case_id, script_id,
                              "None", "None", log_level, tbd)

            target_sut_ip = read_config("SUT_IP", "IP")

            if "FAIL:" in target_sut_ip:
                library.write_log(lib_constants.LOG_WARNING, "WARNING: Failed "
                                  "to get config entries under tag [SUT_IP] for "
                                  "IP", test_case_id, script_id, "None", "None",
                                  log_level, tbd)
                return False
            # time.sleep(30)
            os.chdir(os.getcwd())
            os.system("ping " + target_sut_ip + " > Result.txt")                # Writing the ping status in result.txt file

            flag = 0
            with open("Result.txt", "r") as file_out:                           # Open Result.txt in read mode
                for line in file_out:
                    if "destination host unreachable." in line.lower():
                        flag = 1
                        break
                    elif "could not find" in line.lower():
                        flag = 1
                        break
                    elif "Request timed out." in line.lower():
                        flag = 1
                        break
            if 1 == flag:
                library.write_log(lib_constants.LOG_INFO, "INFO: Unable "
                                  "to ping check for SUT and SUT is in shutdowm"
                                  " state", test_case_id, script_id, "None",
                                  "None", log_level, tbd)
                return True
            else:
                library.write_log(lib_constants.LOG_WARNING, "WARNING: Able to "
                                  "ping SUT sut is not in OFF state",
                                  test_case_id, script_id, "None", "None",
                                  log_level, tbd)
                return False

        library.write_log(lib_constants.LOG_WARNING, "WARNING: Failed to read "
                          "desired post code for shutdown", test_case_id,
                          script_id, "None", "None", log_level, tbd)
        return False

    except Exception as e:
        library.write_log(lib_constants.LOG_ERROR, "EXCEPTION: Due to %s" % e,
                          test_case_id, script_id, "None", "None", log_level,
                          tbd)
        return False


################################################################################
# Function Name : kill_ttk2
# Parameters    : None
# Return Value  : None
# Purpose       : Kill TTK2 service if running
################################################################################


def kill_ttk2():
    try:
        task_list_text_file_path = r"C:\Testing\task_list.txt"
        if os.path.exists(task_list_text_file_path):
            os.remove(task_list_text_file_path)

        os.system('tasklist /FI "IMAGENAME eq TTK2_Server.exe" > %s'
                  % task_list_text_file_path)
        f = open(task_list_text_file_path)
        s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

        if s.find(b"TTK2_Server.exe") != -1:
            print("INFO: TTK2_Server service is running, killing now")
            result = os.system("taskkill /F /IM TTK2_Server.exe")
            if 0 == result:
                time.sleep(1)
                print("PASS: TTK2_Server.exe service killed successfully")
                return True
            else:
                return False
    except Exception as err:
        print("EXCEPTION: due to %s" % err)


def clear_logical_drive():

    try:
        if os.path.exists("S:\\"):
            print("Logical drive Already available for use")
        else:
            command = "mountvol S: /s"
            result = os.system(command)
            time.sleep(10)

        if os.path.exists("S:\\\\startup.nsh"):
            os.remove("S:\\\\startup.nsh")
            print("nsh file removed successfully")
            return True
        else:
            print("nsh file not available in the logical drive")
            return True
    except Exception as e:
        print("EXCEPTION Due to: %s" % e)
        return False


def reset_cswitch(test_case_id, script_id, log_level="ALL", tbd=None):

    try:
        if os.path.exists(lib_constants.SCRIPTDIR + "\\Config.ini"):
            config_path = lib_constants.SCRIPTDIR + "\\Config.ini"
        else:
            config_path = lib_constants.MIDDLEWARE_PATH + "\\Config.ini"

        value = "CSWITCH_ID"
        if os.path.exists(config_path):
            with open(config_path, 'r') as file_:
                data = file_.readlines()

            flag = 0
            cswitch_devices = []

            for i in range(len(data)):
                if "[cswitch]" in data[i].lower():                              # Comparing the Tag Name
                    flag = 1
                    j = i+1

                    while True:
                        if value.lower() in data[j].lower():                    # Comparing whether the Variable is present in the above selected tag or not
                            tag_vale = data[j].split("=")[1].strip()
                            if len(tag_vale) == 0:
                                print("FAIL: Value given is Blank")
                            else:
                                cswitch_devices.append(tag_vale)

                        j = j + 1
                        if j == len(data) or "[" in data[j]:
                            break

            if flag == 0:
                print("WARNING: Values are incorrect or Config.ini does not "
                      "contain the TAG - CSWITCH")
                return True
            else:
                cswitch_unique_id = set(cswitch_devices)
                for each_device in cswitch_unique_id:
                    lib_cswitch.cswitch_unplug(each_device, test_case_id,
                                               script_id, log_level, tbd)
                return True
        else:
            print("FAIL: Config.ini file is not present")
            return False
    except Exception as e:
        print("EXCEPTION Due to: %s" % e)
        return False
