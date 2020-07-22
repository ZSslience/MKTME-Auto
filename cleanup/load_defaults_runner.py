# Global Python Imports
try:
    import mmap
    import os
    import subprocess
    import sys
    import time

    from SoftwareAbstractionLayer import utils
except Exception as e:
    print(e)
    sys.exit(1)

# Global Variables
timeout = 600

try:
    putty_log = r"C:\Testing\GenericFramework\putty.log"
    remote_cmd = r"C:\Testing\GenericFramework\remote.cmd"

    if os.path.exists(putty_log):
        print("%s file exists, removing existing file" % putty_log)
        os.remove(putty_log)
    else:
        print('putty.log file does not exists')

    if os.path.exists(remote_cmd):
        print("%s file exists, removing existing file" % remote_cmd)
        os.remove(remote_cmd)
    else:
        print('remote.cmd file does not exists')
    time.sleep(2)

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
    package_name = package_folder.split("\\")[-1]
    script_file = "load_defaults.py"
    py_interpreter = utils.ReadConfig("PYTHON", "INTERPRETER")
    if not py_interpreter or "FAIL" in py_interpreter:
        py_interpreter = "python"

    command1 = r'cd "c:\\Testing\\GenericFramework\\%s\\cleanup"' % package_name
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
        time.sleep(5)
    except subprocess.TimeoutExpired:
        print("Timeout occurred after %s seconds" % str(timeout))
    finally:
        time.sleep(2)
        kill_task()

    if os.path.exists(putty_log):
        with open(putty_log) as log_file:
            print(log_file.read())

        with open(putty_log) as log_file:
            lines = log_file.readlines()
            for line in lines:
                if "PASS:" in line.upper():
                    sys.exit(0)
                elif "FAIL:" in line.upper() or "EXCEPTION:" in line.upper():
                    sys.exit(1)
                else:
                    continue
    else:
        pass

    sys.exit(1)
except Exception as e:
    print("Exception is: %s" % e)
    time.sleep(1)
    sys.exit(1)
