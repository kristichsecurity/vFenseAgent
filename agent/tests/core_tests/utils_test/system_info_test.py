import platform
import socket
from nose.tools import eq_

from utils import systeminfo


def test_os_code_lowercase():
    """ Test that the os code is returned and lowercase.
    """

    eq_(systeminfo.code(), platform.system().lower(), "os code is not"
                                                            "lowercase.")


def test_os_name():
    """ Test the name of the OS.
    """

    os_code = systeminfo.code()
    os_string = 'Unknown'

    if os_code == 'darwin':
        mac_ver = platform.mac_ver()[0]
        os_string = "OS X %s" % mac_ver

    elif os_code == 'linux':
        distro_info = platform.linux_distribution(
            supported_dists=systeminfo.supported_linux_distros)

        os_string = '%s %s' % (distro_info[0], distro_info[1])

    eq_(systeminfo.name(), os_string, "OS name are not matching.")


def test_bit_type():
    """ Test the bit type (32 or 64 bit arch) of the OS.
    """
    bit_type = systeminfo.bit_type()
    plat_bit_type = platform.architecture()[0][:2]

    eq_(bit_type, plat_bit_type,
        "Bit types don't match: %s != %s" % (bit_type, plat_bit_type))

    assert bit_type in ['64', '32'], "%s not supported." % bit_type


def test_computer_name():
    """ Test computer name.
    """

    computer_name = systeminfo.computer_name()
    sock_name = socket.getfqdn()

    eq_(computer_name, sock_name,
        "Computer names don't match: %s != %s" % (computer_name, sock_name))


def test_hardware():
    """ Test hardware does not return empty string or empty list.
    """

    hardware = systeminfo.hardware()

    assert hardware['cpu'] != [], "Hardware is returning empty CPU."
    assert hardware['memory'] != '', "Hardware is returning empty memory."
    assert hardware['display'] != [], "Hardware is returning empty display."
    assert hardware['nic'] != [], "Hardware is returning empty nic."
    assert hardware['storage'] != [], "Hardware is returning empty storage."


def test_os_version():
    """ Test the os version.
    """

    eq_(systeminfo.version(), platform.release(), "os version does "
                                                  "not match.")