import platform
import subprocess
import socket
import utils.hardware

import logger
from distro import mac


supported_linux_distros = (
    'SuSE', 'debian', 'fedora', 'oracle', 'redhat', 'centos',
    'mandrake', 'mandriva')


class OSCode():

    Mac = "darwin"
    Windows = "windows"
    Linux = "linux"


def code():
    """Gets the os code defined for this system.
    @return: The os code.
    """
    return platform.system().lower()


def name():
    """The "pretty" string of the OS.
    @return: The os string.
    """
    os_code = code()
    os_string = 'Unknown'

    if os_code == OSCode.Mac:
        mac_ver = platform.mac_ver()[0]
        os_string = "OS X %s" % mac_ver

    elif os_code == OSCode.Linux:
        distro_info = platform.linux_distribution(
            supported_dists=supported_linux_distros)

        os_string = '%s %s' % (distro_info[0], distro_info[1])

    return os_string


def version():
    """This returns the kernel of the respective platform.
    @return: The version.
    """
    return platform.release()


def bit_type():
    """The archtecture of the platform. '32' or '64'.
    @return: The bit type.
    """
    return platform.architecture()[0][:2]


def system_architecture():
    """
    Returns a nice string for the system architecture. 'x86_64' or 'i386'
    """
    sys_arch = None

    sys_bit_type = bit_type()

    if sys_bit_type == '64':
        sys_arch = 'x86_64'

    elif sys_bit_type == '32':
        sys_arch = 'i386'

    return sys_arch


def computer_name():
    """The FQDN of the machine.
    @return: The computer name.
    """

    if code() == OSCode.Mac:

        try:
            process = subprocess.Popen(
                ['sysctl', 'kern.hostname'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            output, error = process.communicate()

            output = output.split(':')

            if len(output) > 1:

                return output[1].strip()

        except Exception as e:

            logger.error('Unable to process "sysctl kern.hostname".')
            logger.error('Falling back to socket for hostname.')
            logger.exception(e)

    return socket.getfqdn()


def hardware():
    """Returns the hardware for the system.
    @return: The hardware.
    """
    return utils.hardware.get_hw_info()


def uptime():
    """Gets the current uptime in a platform independent way.

    Returns:
        (long) The uptime in seconds.
    """

    plat = code()
    up = 0

    try:

        if plat == OSCode.Mac:

            up = mac.get_current_uptime()

        elif plat == OSCode.Linux:

            cmd = ['cat', '/proc/uptime']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            raw_output, _stderr = process.communicate()

            secs = raw_output.split()[0]

            # Truncate the decimals for Linux.
            up = long(float(secs))

    except Exception as e:

        logger.error("Could not determine uptime.")
        logger.exception(e)

    return up
