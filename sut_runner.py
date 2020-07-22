__author__ = "Automation Development Team"

# Global Python Imports
try:
    import csv
    import mmap
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

    putty_log = r"C:\Testing\GenericFramework\putty.log"
    if os.path.exists(putty_log):
        print("%s file exists, removing existing file" % putty_log)
        os.remove(putty_log)
    time.sleep(1)

    remote_cmd = r"C:\Testing\GenericFramework\remote.cmd"
    if os.path.exists(remote_cmd):
        print("%s file exists, removing existing file" % remote_cmd)
        os.remove(remote_cmd)
    time.sleep(1)

    def kill_task():
        try:
            putty_text_file_path = r"C:\Testing\putty.txt"
            os.system('tasklist /FI "IMAGENAME eq putty.exe" > %s'
                      % putty_text_file_path)
            f = open(putty_text_file_path)
            s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            if s.find(b"putty.exe") != -1:
                print("Putty service is running, killing now")
                os.system("taskkill /IM putty.exe /F")
        except Exception as err:
            print("EXCEPTION: due to %s" % err)
    kill_task()
    time.sleep(2)

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

    command1 = r'cd "c:\\Testing\\GenericFramework\\%s\\scripts\\%s"' \
        % (package_name, script_folder)
    command2 = r'%s %s' % (py_interpreter, script_file)

    with open(remote_cmd, "w") as cmd_file:
        cmd_file.write(command1)
        cmd_file.write("\n")
        cmd_file.write(command2)
    print("remote.cmd file created successfully")

    try:
        putty_run_command = r"C:\Testing\putty.exe -load DUT_ADD -ssh -l " \
                            r"Administrator -pw intel@1234 -m C:\Testing\Generic" \
                            r"Framework\remote.cmd"
        time.sleep(1)

        process = subprocess.Popen(putty_run_command, shell=True, stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                   bufsize=1, universal_newlines=True)
        output = process.communicate(timeout=timeout)[0]
        time.sleep(2)
    except subprocess.TimeoutExpired:
        time.sleep(2)
        kill_task()
        print("Timeout occurred after %s seconds" % str(timeout))

    if os.path.exists(putty_log):
        with open(putty_log) as log:
            print(log.read())

        with open(putty_log) as log_file:
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
                    kill_task()
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
                    kill_task()
                    time.sleep(1)
                    sys.exit(1)
                else:
                    continue
    else:
        pass

    print("Not found test verdict in sut log")
    time.sleep(1)
    kill_task()
    sys.exit(1)
except Exception as e:
    print("Exception is: %s" % e)
    time.sleep(1)
    sys.exit(1)
