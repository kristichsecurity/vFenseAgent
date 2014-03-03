import os
import signal
import subprocess
import time

from utils import settings
from utils import misc
from utils import systeminfo
from utils import logger

PortRange = reversed(range(10000, 11000))

tunnel_key = os.path.join(settings.CertsDirectory, 'tunnel')
tunnel_pub_key = "%s.pub" % tunnel_key

_ssh_open_tunnels = os.path.join(settings.EtcDirectory, 'open_tunnels')


def _write_ssh_details(host_port, local_port):
    """Writes reverse ssh tunnel data to keep track of open connections.
    """

    try:

        with open(_ssh_open_tunnels, 'w') as open_tunnels:

            open_tunnels.write('%s,%s' % (host_port, local_port))

    except Exception as e:

        logger.error('Unable to write ssh details to file')
        logger.exception(e)


def _read_ssh_details():
    """Reads reverse ssh tunnel data.
    """

    try:

        with open(_ssh_open_tunnels, 'r') as open_tunnels:
            data = open_tunnels.read()

            return data.split(',')

    except Exception as e:

        logger.error('Unable to read ssh details to file')
        logger.exception(e)

    return None, None


def _mac_used_ports():

    used_ports = []

    try:
        process = subprocess.Popen(['lsof', '-i'], stdout=subprocess.PIPE)

        output, error = process.communicate()
        output = output.splitlines()[1:]

        o = [l.split(' ') for l in output]
        data = []
        for l in o:
            data.append([d for d in l if d != ''])

        for d in data:

            try:

                port_info = []

                if len(d) == 9:

                    port_info = d[-1]

                elif len(d) == 10:

                    port_info = d[-2]

                pi = port_info.split(':')
                if len(pi) == 2:

                    if misc.try_long_cast(pi[1]):

                        used_ports.append(long(pi[1]))

                elif len(pi) == 3:

                    if misc.try_long_cast(pi[2]):

                        used_ports.append(long(pi[2]))

                    if misc.try_long_cast(pi[1].split('->')[0]):

                        used_ports.append(pi[1].split('->')[0])

            except Exception as e:

                logger.error('Could not verify port data: %s' % d)
                logger.exception(e)

    except Exception as e:

        logger.error("Could not get used ports.")
        logger.exception(e)

    return used_ports


def get_used_ports():

    if systeminfo.code() == systeminfo.OSCode.Mac:

        return _mac_used_ports()

    elif systeminfo.code() == systeminfo.OSCode.Linux:

        raise NotImplemented('Implement used ports for Linux please.')


def get_available_port():

    for p in PortRange:

        if p in get_used_ports():
            continue

        else:
            return p

    return None


def create_reverse_tunnel(local_port, host_port, server=None, ssh_port=None):

    ssh_output = os.path.join(settings.TempDirectory, 'ssh_output')

    if not ssh_port:
        ssh_port = 22

    try:

        if os.path.exists(ssh_output):
            os.remove(ssh_output)

        # Unfortunately ssh ignores stdin when running in the backgroud
        # (option -f) so we use StrictHostKeyChecking=no just on first
        # connection only. If it changes afterwards an error occurs.

        # And for some reason can't read from stdout with stdout.read()
        # but it writes to file just fine so we read that file instead.

        with open(ssh_output, 'w') as dev_null:
            process = subprocess.Popen(
                [
                    '/usr/bin/ssh', '-oStrictHostKeyChecking=no', '-i',
                    tunnel_key, '-fnNR',
                    '%s:localhost:%s' %
                    (
                        host_port,
                        local_port
                    ),
                    'toppatch@%s' % server,
                    '-p %s' % ssh_port
                ],
                stdout=dev_null,
                stderr=dev_null
            )

            time.sleep(5)

        with open(ssh_output, 'r') as dev_null:
            output = dev_null.read()

            for line in output.splitlines():

                if 'WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!' in line:
                    process.kill()

                    logger.critical("Failed to verify RV ssh host public key.")
                    logger.critical(output)

                    return (
                        False,
                        "Server failed to verify. It's possible"
                        " the ssh host keys changed or, worse, someone could"
                        " be eavesdropping via man-in-the-middle attack."
                        " Terminating ssh tunnel for security reasons. Please"
                        " investigate agent log for further details."
                    )

                elif (
                    'Warning: remote port forwarding failed for listen port' in
                    line
                ):

                    process.kill()

                    logger.critical("Unable to connect to server port."
                                    " Port %s might be in use?" % host_port)
                    logger.critical(output)

                    return (
                        False,
                        "Agent was unable to connect to the specified port. It"
                        " might be in use by another process. Detailed Error: "
                        " %s" % output
                    )

                elif 'Permission denied (publickey)' in line:
                    process.kill()

                    logger.critical("Failed to verify RV ssh host public key.")
                    logger.critical(output)

                    return (
                        False,
                        "Error with the public key: %s" % output
                    )

                elif (
                    'ssh: connect to host' in line
                    and 'port 22: Connection refused' in line
                ):

                    process.kill()

                    msg = (
                        "Failed to connect to ssh. Is the ssh server running"
                        " and listening on port 22?"
                    )

                    logger.critical(msg)
                    logger.critical(output)

                    return (
                        False,
                        msg
                    )

                elif (
                    ("Warning: Identity file %s not accessible" % tunnel_key)
                    in line
                ):

                    process.kill()

                    msg = (
                        "Failed to connect to ssh. Private key was not found."
                    )

                    logger.critical(msg)
                    logger.critical(output)

                    return (
                        False,
                        msg
                    )

            _write_ssh_details(host_port, local_port)
            return True, ''

    except Exception as e:
        logger.error('Could not create ssh tunnel.')
        logger.exception(e)
        return False, 'Unable to create ssh tunnel. %e' % str(e)


def create_keys(override=False):
    """Creates the private and public keys used for tunneling.

    Args:

        - override: If True, any existing keys are overridden. If False,
            existing keys are kept and nothing is done.

    Returns:

        - True if new keys are created. False otherwise.

    """

    private_exist = os.path.exists(tunnel_key)
    public_exist = os.path.exists(tunnel_pub_key)

    if(
        not override
        and private_exist
        and public_exist
    ):

        return False

    try:

        cmd = [
            '/usr/bin/ssh-keygen',
            '-t', 'rsa',
            '-N', '',  # Empty passphrase
            '-f', tunnel_key
        ]

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        process.communicate(input='y')

    except Exception as e:

        logger.error('Unable to create ssh keys.')
        logger.exception(e)

        return False


def stop_reverse_tunnel():

    try:

        port1, port2 = _read_ssh_details()

        process = subprocess.Popen(
            [
                '/bin/ps', '-fe'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        output, error = process.communicate()

        for o in output.splitlines():

            if (
                'ssh' in o
                and port1 in o
                and port2 in o
            ):

                line = [l for l in o.split(' ') if l != '']
                if len(line) >= 2:

                    os.kill(int(line[1]), signal.SIGTERM)
                    return True

    except Exception as e:

        logger.error('Unable to stop existing tunnel.')
        logger.exception(e)

    return False
