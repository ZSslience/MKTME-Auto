import pythonsv_icx_handler as itp_sv


# x = itp_sv.get_msr(0x35)
# x = get_msr(0x35)
itp, sv = itp_sv.pythonsv_init()
x = itp.threads[0].msr(0x35)
print('MSR 0x35: %s' % x)
itp_sv.pythonsv_exit()