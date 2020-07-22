__author__ = r'yusufmox\tnaidux'

# Global Python Imports
import os
import shutil
import subprocess
import sys
import zipfile

# Local Python Imports
import cleanup

CONFIG_FILE = "Config.ini"

try:
    def find_file(root, filename):
        ret = []
        if not os.path.exists(root):
            return ret
        for root, _, files in os.walk(root):
            for f in files:
                if f == filename:
                    ret.append(os.path.join(root, f))
        return ret

    current_folder = os.path.dirname(os.path.abspath(sys.argv[0]))
    dst_config_file = os.path.join(current_folder, CONFIG_FILE)
    if not os.path.exists(dst_config_file):
        case_root = os.path.realpath(os.path.dirname(current_folder))
        script_configs = find_file(case_root, CONFIG_FILE)

        if not script_configs:
            print("Warning: Cannot find Config.ini in %s" % case_root)
        else:
            src_config_file = script_configs[0]
            shutil.copyfile(src_config_file, dst_config_file)

    main_directory = r"C:\Testing\GenericFramework"
    extension = ".zip"

    current_src_path = os.getcwd()
    src_path = current_src_path + extension
    print("src_path is: %s" % src_path)

    src_path_size = os.path.getsize(src_path)
    print("src_path file size is %s" % str(src_path_size))

    dst_package = src_path.split(os.sep)[-1]
    print("dst_package is: %s" % dst_package)

    dst_path = r"Z:\GenericFramework" + os.sep + dst_package
    print("dst_path is: %s" % dst_path)

    csv_file = src_path + "\\" + dst_package + ".csv"
    if os.path.exists(csv_file):
        print("Removing Previous Package Run CSV file")
        os.remove(csv_file)

    destination_log_folder = r"C:\Testing\GenericFramework\Logs" + "\\" + \
        dst_package
    if os.path.exists(destination_log_folder):
        print("Removing Previous Package Run folder in"
              "C:\Testing\GenericFramework\Logs")
        shutil.rmtree(destination_log_folder)

    cleanup.kill_ttk2()

    copy_command = "echo F|xcopy /S /E /Y /V /Q /F /Z " + src_path + " " + \
        dst_path
    print("copy_command is: %s" % copy_command)

    result = subprocess.Popen(copy_command, shell=True, stdin=subprocess.PIPE,
                              stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    output = result.communicate()[0]
    returncode = int(result.returncode)

    if 0 == returncode:
        if os.path.exists(dst_path):
            dst_path_size = os.path.getsize(dst_path)
            print("dst_path length is %s" % str(dst_path_size))

            if dst_path_size == src_path_size:
                print("File Operation performed Successfully\n"
                      "Compared length of %s & %s, Both files are same" %
                      (src_path, dst_path))
                if os.path.exists(dst_path):
                    with zipfile.ZipFile(dst_path, "r") as zip_ref:
                        dst_folder = current_src_path.split(os.sep)[-1]
                        dst_folder = r"Z:\\GenericFramework\\%s" % dst_folder
                        if os.path.exists(dst_folder):
                            print("%s already exists, remove it" % dst_folder)
                            shutil.rmtree(dst_folder)
                        zip_ref.extractall(dst_folder)
                        if os.path.exists(dst_folder):
                            print("\n%s unzipped successfully" % dst_path)
                            sys.exit(0)
                        else:
                            print("Failed to unzip the copied package")
                            sys.exit(1)
            else:
                print("File copy is not successful")
                sys.exit(1)
    else:
        print("Failed to Perform File Operations")
        sys.exit(1)
except Exception as e:
    print("Exception: Due to %s" % e)
    sys.exit(1)
