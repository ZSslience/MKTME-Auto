__author__ = "jkmody"

# Global Python Imports
import subprocess
import sys
import time

try:
    count = 0
    steps = 4

    print("###################################################################")
    print("Executing: %s" % "python.exe ./cleanup/boot_to_os_host.py")

    command = "python.exe ./cleanup/boot_to_os_host.py"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.communicate()[0]
    time.sleep(2)
    print(output)

    if "PASS:" in output:
        count = count + 1

    print("###################################################################")
    print("Executing: %s" % "python.exe ./cleanup/load_defaults_runner.py")

    command = "python.exe ./cleanup/load_defaults_runner.py"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.communicate()[0]
    time.sleep(2)
    print(output)

    if "PASS:" in output:
        count = count + 1

    print("###################################################################")
    print("Executing: %s" % "python.exe ./cleanup/remote_reboot.py")

    command = "python.exe ./cleanup/remote_reboot.py"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.communicate()[0]
    time.sleep(2)
    print(output)

    if "PASS:" in output:
        count = count + 1

    print("###################################################################")
    print("Executing: %s" % "python.exe ./cleanup/reset_relay.py")

    command = "python.exe ./cleanup/reset_relay.py"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.communicate()[0]
    time.sleep(2)
    print(output)

    if "PASS:" in output:
        count = count + 1

    if count == steps:
        print("PASS: Successfully Executed Clean up Scenarios")
        sys.exit(0)
    else:
        print("FAIL: Execution Failed for Cleanup Scenarios")
        sys.exit(1)
except Exception as e:
    print("ERROR: Unable to Execute the Package: due to %s." % e)
    sys.exit(1)
