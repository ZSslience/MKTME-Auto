import os
import re


def test_memmap_parse(log_file, query_string):
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding="utf_16_le") as buf:
            map_data = buf.read()
        data = map_data.split('\n')
        search_string = r'(.*) (.*)-(.*) (.*) (.*)'
        ret_list = list(filter(lambda x: re.match(search_string, x) is not None, data))
        ret_index = [ret_list.index(line) for line in ret_list if query_string in line]
        if len(ret_index) == 0:
            return None, len(ret_list), ret_list
        return ret_index[-1], len(ret_list), ret_list


if __name__ == '__main__':
    a, b , c = test_memmap_parse(r'C:\Users\sys_eval\Desktop\qiuzhong\1507268867_Step_5.log', '000000000000000F')
    print(a)
    print(b)