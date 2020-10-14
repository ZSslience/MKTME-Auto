import sys
from scripts.common.xplatform import XSetup

if sys.argv[1] == 'ac_on':
    result = XSetup.do_ac_on()
    if not result:
        exit(1)
    else:
        exit(0)

elif sys.argv[1] == 'ac_off':
    result = XSetup.do_ac_off()
    if not result:
        exit(1)
    else:
        exit(0)


