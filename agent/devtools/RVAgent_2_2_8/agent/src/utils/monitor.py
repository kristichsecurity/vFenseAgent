# THIS MODULE IS OBSOLETE!!!!

import subprocess

from utils import logger
#from utils.distro.mac.macmonitor import mac_monitor_data
from utils import systeminfo


def calculate_percentage(total, diff):

    if total == 0:
        return 0

    return str(round(100 * float(diff) / float(total), 2))


def _get_fs_data():

    cmd = ['df', '-hklT']

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    raw_output, errors = process.communicate()
    lines = []
    output = []

    for line in raw_output.splitlines():
        lines.append([x for x in line.split(' ') if x != ''])

    _partition_blacklist = [
        'tmpfs',
        'rootfs',
        'none',
        'devtmpfs',
        'Filesystem'
    ]

    for i in range(len(lines)):

        if len(lines[i]) == 7:

            output.append(lines[i])

        if len(lines[i]) == 1:

            if len(lines[i + 1]) == 6:

                lines[i].extend(lines[i + 1])

                output.append(lines[i])

    fs_data = []

    for entry in output:

        if entry[0] in _partition_blacklist:
            continue

        try:

            # An ideal entry would consist of 7 items. It would look like:
            # ['/dev/sda1', 'ext4', '495844', '38218', '432026', '9%', '/boot']
            if len(entry) == 7:

                name = entry[0]
                total = int(entry[3]) + int(entry[4])

                used = entry[3]
                percent_used = calculate_percentage(total, used)

                available = entry[4]
                percent_available = calculate_percentage(total, available)

                mount = entry[6]

                fs_data.append(
                    (name,
                     str(used), percent_used,
                     str(available), percent_available,
                     mount)
                )

        except Exception as e:

            logger.error(
                "Could not read file system data '%s'. Skipping." % entry
            )
            logger.exception(e)

    return fs_data


def get_file_system_data():

    fs_list = []

    try:

        fs_data = _get_fs_data()

        for fs in fs_data:

            fs_dict = {}

            fs_dict['name'] = fs[0]
            fs_dict['used'] = fs[1]
            fs_dict['used_percent'] = fs[2]
            fs_dict['free'] = fs[3]
            fs_dict['free_percent'] = fs[4]
            fs_dict['mount'] = fs[5]

            fs_list.append(fs_dict.copy())
    except Exception as e:

        logger.error("Could not retrieve file system data.")
        logger.exception(e)

    return fs_list


def get_cpu_usage():

    return {'user': 0, 'system': 0, 'idle': 0}


def get_monitor_data():

    data = {}

    if systeminfo.code() == systeminfo.OSCode.Mac:
        #data = mac_monitor_data()
        pass

    else:

        root = {}
        root['memory'] = {'used': 0, 'used_percent': 0,
                          'free': 0, 'free_percent': 0}

        root['cpu'] = get_cpu_usage()

        root['file_system'] = get_file_system_data()

        data = root

    return data
