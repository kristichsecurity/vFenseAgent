import time
import subprocess

from utils import logger

from monitor.monitoperation import MonitKey


def try_long_cast(string):
    """Wrapper to cast a string into a long. No try/except all over the place.

     Returns:
        (bool) True if cast is successful. False otherwise.
    """
    try:
        long(string)
        return True
    except ValueError:
        return False


# def mac_monitor_data():
#
#     root = {}
#
#     m = MacMonitor()
#
#     used, used_percent, free, free_percent = m.memory_usage()
#     root['memory'] = {'used': used, 'used_percent': used_percent,
#                       'free': free, 'free_percent': free_percent}
#
#     user, sys, idle = m.cpu_usage()
#     root['cpu'] = {'user': user, 'system': sys, 'idle': idle}
#
#
#     fs_data = m.filesystem_usage()
#     fs_list = []
#     for fs in fs_data:
#
#         fs_dict = {}
#
#         fs_dict['name'] = fs[0]
#         fs_dict['used'] = fs[1]
#         fs_dict['used_percent'] = fs[2]
#         fs_dict['free'] = fs[3]
#         fs_dict['free_percent'] = fs[4]
#         fs_dict['mount'] = fs[5]
#
#         fs_list.append(fs_dict.copy())
#
#     root['file_system'] = fs_list
#
#     return root


class MacMonitor():

    def __init__(self):

        self.top_cmd = ['top']
        self.df_cmd = ['df', '-kl']
        self.refresh_stats()

    def refresh_stats(self):

        process = subprocess.Popen(self.df_cmd, stdout=subprocess.PIPE)
        self.df_output, _error = process.communicate()

        # process = subprocess.Popen(self.top_cmd, stdout=subprocess.PIPE)
        # time.sleep(1.0)
        # process.terminate()
        # self.top_output, _error = process.communicate()

    def current_cpu_data(self):
        # Example output /usr/sbin/iostat:
        #       disk0       cpu     load average
        #  KB/t tps  MB/s  us sy id   1m   5m   15m
        # 23.39   3  0.08   7  4 89  0.81 0.69 0.53

        # Following logic is based on the above output. That no other
        # stat will appear before "cpu" that is named with two strings.
        # Such as "load average".

        try:

            cpu_index = None
            cmd = ['/usr/sbin/iostat']
            io = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]

            top_line = io.splitlines()[0]
            top_line = [l for l in top_line.split(' ') if l != '']

            for i in range(len(top_line)):
                if top_line[i] == 'cpu':
                    cpu_index = i * 3  # 3 becuase of the output in iostat
                    break              # uses 3 units per device.

            stats_line = io.splitlines()[2]
            stats_line = [l for l in stats_line.split(' ') if l != '']

            stats = {

                MonitKey.User: stats_line[cpu_index],
                MonitKey.System: stats_line[cpu_index + 1],
                MonitKey.Idle: stats_line[cpu_index + 2]
            }

        except Exception as e:

            logger.error("Could not get mac cpu data.")
            logger.exception(e)

            stats = {

                MonitKey.User: 0,
                MonitKey.System: 0,
                MonitKey.Idle: 0
            }

        return stats

    def current_memory_data(self):
        # Example output for /usr/bin/vm_stat
        # Mach Virtual Memory Statistics: (page size of 4096 bytes)
        # Pages free:                        2722765.
        # Pages active:                       744379.
        # Pages inactive:                      95171.
        # Pages speculative:                  214667.
        # Pages wired down:                   416830.
        # "Translation faults":             58177385.
        # Pages copy-on-write:               1083635.
        # Pages zero filled:                24278737.
        # Pages reactivated:                    1069.
        # Pageins:                           2184851.
        # Pageouts:                                0.
        # Object cache: 13 hits of 76100 lookups (0% hit rate)

        vm_stat_cmd = ['/usr/bin/vm_stat']
        bytes_in_page = 4096

        try:

            process = subprocess.Popen(vm_stat_cmd, stdout=subprocess.PIPE)
            vm_stat_output, _error = process.communicate()

            lines = vm_stat_output.splitlines()[1:6]

            data = []

            lines = [l.partition(':')[2] for l in lines]
            lines = [l.split(' ') for l in lines]
            for line in lines:
                for i in line:
                    if i != '':
                        data.append(float(i[:-1]))

            # Expected order: free, active, inactive, speculative, wired
            free = data[0] * bytes_in_page
            active = data[1] * bytes_in_page
            inactive = data[2] * bytes_in_page
            speculative = data[3] * bytes_in_page
            wired = data[4] * bytes_in_page

            total = free + active + inactive + speculative + wired
            real_free = free + speculative
            used = total - real_free

            percent_used = self.calculate_percentage(total, used)
            percent_free = self.calculate_percentage(total, real_free)
            used_kb = str(round(used / 1024, 2))
            free_kb = str(round(real_free / 1024, 2))

            stats = {
                MonitKey.Used: used_kb,
                MonitKey.PercentUsed: percent_used,
                MonitKey.Free: free_kb,
                MonitKey.PercentFree: percent_free
            }

        except Exception as e:

            logger.error("Could not get mac memory data.")
            logger.exception(e)

            stats = {
                MonitKey.Used: 0,
                MonitKey.PercentUsed: 0,
                MonitKey.Free: 0,
                MonitKey.PercentFree: 0
            }

        return stats

    def filesystem_usage(self):

        _ignore_keywords = ['map', 'Filesystem', 'devfs', 'tempfs', '-hosts',
                            'auto_home']

        outlines = []

        process = subprocess.Popen(self.df_cmd, stdout=subprocess.PIPE)
        self.df_output, _error = process.communicate()

        # Nifty way to remove all the spaces in the output.
        for line in self.df_output.splitlines():
            outlines.append([x for x in line.split(' ') if x != ''])

        fs_data = []
        for line in outlines:

            name = ''
            used = 0
            percent_used = 0
            available = 0
            percent_available = 0
            mount = ''

            if line[0] in _ignore_keywords:
                continue

            for i in range(len(line)):

                if not try_long_cast(line[i]):
                    name = "%s %s" % (name, line[i])
                    name = name.strip()
                    continue

                # + n to skip over the 'blocks' digit
                used = long(line[i + 1])
                available = long(line[i + 2])
                mount = line[i + 4]

                percent_used = self.calculate_percentage(
                    used + available,
                    used
                )
                percent_available = self.calculate_percentage(
                    used + available,
                    available
                )

                break

            fs_data.append((name,
                            str(used), percent_used,
                            str(available), percent_available,
                            mount))

        return fs_data

    def current_filesystem_data(self):

        fs_list = []

        try:

            fs_data = self.filesystem_usage()

            for fs in fs_data:

                fs_dict = {}

                fs_dict[MonitKey.Name] = fs[0]
                fs_dict[MonitKey.Used] = fs[1]
                fs_dict[MonitKey.PercentUsed] = fs[2]
                fs_dict[MonitKey.Free] = fs[3]
                fs_dict[MonitKey.PercentFree] = fs[4]
                fs_dict[MonitKey.Mount] = fs[5]

                fs_list.append(fs_dict.copy())

        except Exception as e:

            logger.error("Could not retrieve mac file system data.")
            logger.exception(e)

        return fs_list

    def calculate_percentage(self, total, diff):

        if total == 0:
            return 0

        return str(round(100 * float(diff) / float(total), 2))
