__author__ = "jkmody"

# Global Python Import
try:
    import csv
    import os
    import socket
    import sys
except Exception as e:
    print(e)
    sys.exit(1)

try:
    host_name = socket.gethostname()
    folder_path = os.getcwd()
    log_path = []
    csv_name = folder_path.split("\\")[-1]
    tc_excel_file = folder_path + "\\" + csv_name + ".csv"
    tc_html_file = folder_path + "\\" + csv_name + ".html"
except Exception as e:
    print(e)
    sys.exit(1)


def tc_summary(csvfile):

    try:
        tc_id = []
        fail_tc_id = []
        pass_tc_id = []

        with open(tc_excel_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if not row:
                    continue
                if row[0] not in tc_id and 'Test Case ID' not in row:
                    tc_id.append(row[0])

        with open(tc_excel_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if not row:
                    continue
                for i in range(len(tc_id)):
                    if tc_id[i] in row[0] and "FAIL" in row[3] and \
                       'Test Case ID' not in row and tc_id[i] not in \
                       fail_tc_id:
                        fail_tc_id.append(tc_id[i])
                    else:
                        pass

        pass_tc_id = list(set(tc_id) - set(fail_tc_id))
        return len(tc_id), len(fail_tc_id), len(pass_tc_id)
    except Exception as e:
        print(e)
        sys.exit(1)


try:
    tc_count, fail_tc_count, pass_tc_count = tc_summary(tc_excel_file)

    summary_header = ['Total  No. Of  TCs', "PASS", "FAIL"]
    system_details_header = ['Host name']
    summary_string = ''

    table_string = '''
    <html>
    <head>
    <style>
    table, th, td {
      border: 1px solid black;
    }

    th {
      background-color: #357EC7;
      color: white;
    }
    </style>
    </head>
    <body>

    <header>
      <br style = "line-height:1;">
      <h1><center>Automation Execution Report</center></h1>
      <h2><center>SSP FID FIV CIV BA</center></h2>
      <br style = "line-height:3;">
      <h1>Execution Summary</h1>
    </header>

    <table style="width:25%">\n'''
    summary_string += "<tr>" + \
        "<th>" + \
        "</th><th>".join(system_details_header) + \
        "</th>" + \
        "</tr>\n<tr>\n<td>"

    summary_string += host_name
    summary_string += "</td>\n</tr>\n</table>\n<br style = 'line-height:1;'>\n"

    summary_string += '<table style="width:25%">\n<tr>' + \
        "<th>" + \
        "</th><th>".join(summary_header) + \
        "</th>" + \
        "</tr>\n<tr>\n<td>"

    summary_string += str(tc_count)
    summary_string += "</td><td>"
    summary_string += str(pass_tc_count)
    summary_string += "</td><td>"
    summary_string += str(fail_tc_count)
    summary_string += \
        "</td>\n</tr>\n</table>\n<br style = 'line-height:3;'>\n" \
        "<h1>Detailed Execution Summary</h1>\n<table style='width:75%'>\n"

    table_string += summary_string
    with open(tc_excel_file, 'r') as csvfile:
        reader = csv.reader(csvfile)
        log_path_count = 0
        for row in reader:
            if not row:
                continue
            if "Result" in row:
                table_string += "<tr>" + \
                    "<th style='width:12%'>" + \
                    "</th><th>".join(row) + \
                    "</th>" + \
                    "</tr>\n"
            else:
                table_string += "<tr>" + \
                    "<td>"

                table_string += row[0]
                table_string += "</td><td>"
                table_string += row[1]
                table_string += "</td><td>"
                table_string += row[2]
                table_string += "</td>"

                if "PASS" in row:
                    table_string += "<td bgcolor='green'>"
                else:
                    table_string += "<td bgcolor='red'>"

                table_string += "</td></tr>"
                log_path_count = log_path_count + 1

    table_string += '''

    </table>\n
    <br style = "line-height:1;">
    <footer>
        <p>Contact information: <a href="mailto:jaimin.k.mody@intel.com">
          Mody, Jaimin K </a>.</p>
    </footer>
    </body\n
    </html>'''

    with open(tc_html_file, 'w') as htmlfile:
        htmlfile.write(table_string)

    print("\n###############################################################\n")
    print("\nSuccessfully Created %s Log file" % str(htmlfile))
    print("\n###############################################################\n")
    sys.exit(0)
except Exception as e:
    print("EXCEPTION: Due to %s" % e)
    sys.exit(1)
