import subprocess
from datetime import datetime
from utils import logger


def get_current_uptime():
    """Gets the current uptime in seconds.

    Returns:
        (long) The uptime in seconds.
    """

    cmd = ['/usr/sbin/sysctl', 'kern.boottime']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    raw_output, _stderr = process.communicate()
    raw_output = raw_output.replace(',', '')

    # Example output:
    # kern.boottime: { sec = 1364141103, usec = 0 } Sun Mar 24 12:05:03 2013
    # kern.boottime: { sec = 1364959488, usec = 0 } Tue Apr  2 23:24:48 2013
    # We want what 'sec' == to.

    date = raw_output.partition('=')[2].strip().split(' ')[0]

    delta = datetime.now() - datetime.fromtimestamp(float(date))

    return delta.seconds

