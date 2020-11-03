import pythonsv_icx_handler as itp_sv


def itp_ctrl(status="open"):
    if status == "open":
        itp_sv.pythonsv_init()
        return True
    elif status == "close":
        itp_sv.pythonsv_exit()
        return True
    else:
        return False


def test_cpuid(id=0x7, idx=0, target="ecx", step_string="reading CPUID: ", complete=False):
    try:
        result = cpuid(id, idx)
        print(result)
    except Exception:
        sys.exit(1)


def test_itp_msr(id=0x982, idx=0, step_string="reading itp.threads.msr MSR: ", complete=False):
    try:
        result = itp.threads[idx].msr(id)
        return result
    except Exception:
        print('test itp msr error')
        sys.exit(2)


def test_all():
    itp_ctrl('open')
    test_cpuid()
    itp_ctrl('close')


if __name__ == '__main__':
    test_all()

