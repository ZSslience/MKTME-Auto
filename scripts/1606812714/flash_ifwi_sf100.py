'''Flash BIOS IFWI via SF100 device sampel'''

from MiddleWare import lib_flash_server

def flash_ifwi_via_sf100(ifwi):
    if not lib_flash_server.flash_bmc(ifwi):
        print('Failed to flash BIOS IFWI via SF100')
    else:
        print('Succeed to flash BIOS IFWI via SF100')


if __name__ == '__main__':
    ifwi = r'C:\Users\sys_eval\Desktop\qz\IDVLCRB.86B.OR.64.2020.38.3.16.0805_0017.D18_P_LCC_CDF.bin'
    flash_ifwi_via_sf100(ifwi)
