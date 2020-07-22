__author__ = "Automation Development Team"

# Global Python Imports
try:
    import csv
    import os
    import subprocess
    import sys
    import time

    from SoftwareAbstractionLayer import utils
except Exception as e:
    print(e)
    sys.exit(1)

try:
    script_path = sys.argv[1]
    timeout = int(sys.argv[2])
    step_name = str(sys.argv[3]).replace("+", " ")
except IndexError:
    timeout = int(600)
    script_path = "None"
    step_name = "None"

try:
    if "," in str(step_name):
        step_name = str(step_name.replace(",", "&"))

    host_log = r"C:\Testing\GenericFramework\host.log"
    if os.path.exists(host_log):
        os.remove(host_log)
    time.sleep(1)

    package_folder = os.getcwd()
    print("package_folder: %s" % package_folder)
    package_name = package_folder.split("\\")[-1]
    print("package_name: %s" % package_name)
    script_file = script_path.replace("/", "\\").split("\\")[-1]
    print("script_file: %s" % script_file)
    script_folder = script_path.replace("/", "\\").split("\\")[-2]
    print("script_folder: %s" % script_folder)
    py_interpreter = utils.ReadConfig("PYTHON", "INTERPRETER")
    if not py_interpreter or "FAIL" in py_interpreter:
        py_interpreter = "python"

    def kill_task(proc_pid):
        try:
            print("Process pid = {pid}".format(pid=proc_pid))
            print("Terminates the process and any child processes")
            os.popen("TASKKILL /F /PID {pid} /T".format(pid=proc_pid))
        except Exception as err:
            print("EXCEPTION: due to %s" % err)

    process = None
    try:
        if os.path.isabs(script_path):
            command = r"%s %s\scripts\%s\%s > %s 2>&1" % \
                (py_interpreter, package_folder, script_folder, script_file, host_log)
        else:
            command = r"%s %s > %s" % (py_interpreter, script_path, host_log)
        print("Script path command is: %s" % command)
        time.sleep(1)

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                   bufsize=1, universal_newlines=True)

        output = process.communicate(timeout=timeout)[0]
        time.sleep(2)
    except subprocess.TimeoutExpired:
        kill_task(process.pid)
        print("Timeout occurred after %s seconds" % str(timeout))

    if os.path.exists(host_log):
        with open(host_log) as log:
            print(log.read())

        with open(host_log) as log_file:
            lines = log_file.readlines()
            for line in lines:
                if "PASS:" in line:
                    os.chdir(package_folder)
                    csv_file_path = package_folder + os.sep + \
                        package_name + ".csv"

                    if os.path.exists(csv_file_path):
                        with open(csv_file_path, "a") as csv_file:
                            filewriter = \
                                csv.writer(csv_file, delimiter=',',
                                           quotechar='|',
                                           quoting=csv.QUOTE_MINIMAL)
                            filewriter.writerow([script_folder,
                                                 script_file, step_name,
                                                 "PASS"])
                    else:
                        with open(csv_file_path, "w") as csv_file:
                            filewriter = \
                                csv.writer(csv_file, delimiter=',',
                                           quotechar='|',
                                           quoting=csv.QUOTE_MINIMAL)
                            filewriter.writerow(["Test Case ID",
                                                 "Script ID", "Step",
                                                 "Result"])
                            filewriter.writerow([script_folder,
                                                 script_file, step_name,
                                                 "PASS"])
                    time.sleep(1)
                    sys.exit(0)
                elif "FAIL:" in line or "EXCEPTION:" in line:
                    os.chdir(package_folder)
                    csv_file_path = package_folder + os.sep + \
                        package_name + ".csv"

                    if os.path.exists(csv_file_path):
                        with open(csv_file_path, "a") as csv_file:
                            filewriter = \
                                csv.writer(csv_file, delimiter=',',
                                           quotechar='|',
                                           quoting=csv.QUOTE_MINIMAL)
                            filewriter.writerow([script_folder,
                                                 script_file, step_name,
                                                 "FAIL"])
                    else:
                        with open(csv_file_path, "w") as csv_file:
                            filewriter = \
                                csv.writer(csv_file, delimiter=',',
                                           quotechar='|',
                                           quoting=csv.QUOTE_MINIMAL)
                            filewriter.writerow(["Test Case ID",
                                                 "Script ID", "Step",
                                                 "Result"])
                            filewriter.writerow([script_folder,
                                                 script_file, step_name,
                                                 "FAIL"])
                    time.sleep(1)
                    sys.exit(1)
                else:
                    continue
    else:
        pass

    print("Not found test verdict in host log")
    time.sleep(1)
    sys.exit(1)
except Exception as e:
    print("Exception is: %s" % e)
    sys.exit(1)
