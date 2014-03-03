import json
import subprocess

from agentplugin import AgentPlugin
from utils import RepeatTimer, logger, settings, systeminfo

from serveroperation.sofoperation import RequestMethod

from monitor.monitoperation import MonitOperation, MonitOperationValue
from monitor.monitoperation import MonitKey, MonitUrn

from monitor.mac.macmonitor import MacMonitor


class MonitorPlugin(AgentPlugin):

    Name = 'monitor'

    def __init__(self):

        self._name = MonitorPlugin.Name

        self._previous_user_cpu = 0
        self._previous_sys_cpu = 0
        self._previous_idle_cpu = 0
        self._previous_total_cpu = 0

        if systeminfo.code() == systeminfo.OSCode.Mac:

            self._mac_monitor = MacMonitor()

        else:

            self._mac_monitor = None

    def start(self):
        """Runs once the agent core is initialized.

        Returns:

            - Nothing

        """

        self._timer = RepeatTimer(
            300,  # 300 seconds == 5 minutes
            self._create_monit_operation
        )
        self._timer.start()

    def stop(self):
        """Runs once the agent core is shutting down.

        Returns:

            - Nothing

        """

        logger.error("stop() method not implemented.")

    def run_operation(self, operation):
        """Executes an operation given to it by the agent core.

        Returns:

            - Nothing

        """

        logger.debug("agent-id: {0}, agent-version: {1}"
                     .format(settings.AgentId, settings.AgentVersion))

        if not isinstance(operation, MonitOperation):
            operation = MonitOperation(operation.raw_operation)

        if operation.type == MonitOperationValue.MonitorData:
            monit_data = self.get_monit_data()

            operation.raw_result = json.dumps(monit_data)
            operation.urn_response = MonitUrn.get_monit_data_urn()
            operation.request_method = RequestMethod.POST

        else:
            logger.warning("Unknown operation %s. Ignoring." % operation.type)

        self._send_results(operation, retry=False)

    def initial_data(self, operation_type):
        """Any initial data the server should have on first run.

        Args:
            operation_type - The type of operation determines what the plugin
                             should return. Currently ignored for MonitPlugin.

        Returns:
            (dict) Dictionary with monitoring data.

        """
        logger.debug("Getting initial monitoring data.")

        data = self.get_monit_data()

        logger.debug("Done with initial monitoring data.")

        return data

    def get_monit_data(self):
        """Gets the given operation with all monitoring data.

        Returns:

            - Dictionary containing monitoring data.

        """

        logger.debug("Gathering monitoring data.")

        #operation.memory = self.current_memory_data()
        #operation.cpu = self.current_cpu_data()
        #operation.file_system = self.current_filesystem_data()

        monit_data = {}
        monit_data['memory'] = self._get_memory_data()
        monit_data['cpu'] = self._get_cpu_data()
        monit_data['file_system'] = self._get_file_system_data()

        logger.debug("Done gathering monitoring data.")

        return {'data': monit_data}

    def _get_memory_data(self):
        memory = self.current_memory_data()

        memory['used_percent'] = float(memory['used_percent'])
        memory['free_percent'] = float(memory['free_percent'])
        memory['used'] = float(memory['used'])
        memory['free'] = float(memory['free'])

        return memory

    def _get_cpu_data(self):
        cpu = self.current_cpu_data()

        cpu['idle'] = float(cpu['idle'])
        cpu['user'] = float(cpu['user'])
        cpu['system'] = float(cpu['system'])

        return cpu

    def _get_file_system_data(self):
        file_system = self.current_filesystem_data()

        for fs in file_system:
            fs['used_percent'] = float(fs['used_percent'])
            fs['free_percent'] = float(fs['free_percent'])
            fs['used'] = float(fs['used'])
            fs['free'] = float(fs['free'])

        return file_system

    def _create_monit_operation(self):
        """A wrapper method to create a monit operation and register
        it with the core.

        Returns:

            - Nothing

        """

        if settings.AgentId:
            operation = MonitOperation()
            operation.type = MonitOperationValue.MonitorData
            self._register_operation(operation.to_json())

    def current_memory_data(self):
        """Gets the current memeory stats.

        Returns:

            - Memory data dict using applicable MonitKey keys.

        """

        if self._mac_monitor:

            return self._mac_monitor.current_memory_data()

        cmd = ['cat', '/proc/meminfo']

        try:

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

            output, errors = process.communicate()

            mem_info = output.splitlines()[:2]

            total_memory = 0
            total_free = 0

            for info in mem_info:

                if 'MemTotal:' in info:

                    total_info = info.partition(':')[2].rsplit(' ')[-2:]
                    total = total_info[0]
                    units = total_info[1]

                    if 'kB' in units:

                        total_memory = long(total)
                        continue

                elif 'MemFree:' in info:

                    free_info = info.partition(':')[2].rsplit(' ')[-2:]
                    free = free_info[0]
                    units = free_info[1]

                    if 'kB' in units:

                        total_free = long(free)
                        continue

            total_used = total_memory - total_free

            used_percent = self.calculate_percentage(total_memory, total_used)
            free_percent = self.calculate_percentage(total_memory, total_free)

            stats = {
                MonitKey.Used: total_used,
                MonitKey.PercentUsed: used_percent,
                MonitKey.Free: total_free,
                MonitKey.PercentFree: free_percent
            }

        except Exception as e:

            logger.error("Could not get memory data.")
            logger.exception(e)

            stats = {
                MonitKey.Used: 0,
                MonitKey.PercentUsed: 0,
                MonitKey.Free: 0,
                MonitKey.PercentFree: 0
            }

        return stats

    def current_cpu_data(self):
        """Gets the current cpu stats.

        Returns:

            - Cpu data dict using applicable MonitKey keys.

        """

        if self._mac_monitor:

            return self._mac_monitor.current_cpu_data()

        cmd = ['cat', '/proc/stat']

        try:

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

            output, errors = process.communicate()

            cpu = output.splitlines()[0]
            cpu_numbers = cpu.split(' ')[2:]

            current_total = 0
            for usage in cpu_numbers:

                current_total += long(usage)

            total = current_total - self._previous_total_cpu

            current_user = long(cpu_numbers[0]) + long(cpu_numbers[1])
            current_sys = long(cpu_numbers[2])
            current_idle = long(cpu_numbers[3])

            user = current_user - self._previous_user_cpu
            sys = current_sys - self._previous_sys_cpu
            idle = current_idle - self._previous_idle_cpu

            self._previous_total_cpu = current_total
            self._previous_user_cpu = current_user
            self._previous_sys_cpu = current_sys
            self._previous_idle_cpu = current_idle

            stats = {
                MonitKey.User: self.calculate_percentage(total, user),
                MonitKey.System: self.calculate_percentage(total, sys),
                MonitKey.Idle: self.calculate_percentage(total, idle)
            }

        except Exception as e:

            logger.error("Could not get cpu data.")
            logger.exception(e)

            stats = {

                MonitKey.User: 0,
                MonitKey.System: 0,
                MonitKey.Idle: 0
            }

        return stats

    def current_filesystem_data(self):
        """Gets the current file system stats.

        Returns:

            - File system data dict using applicable MonitKey keys.

        """

        if self._mac_monitor:

            return self._mac_monitor.current_filesystem_data()

        stats = []

        try:

            fs_data = self._get_fs_data()

            for fs in fs_data:

                fs_dict = {}

                fs_dict[MonitKey.Name] = fs[0]
                fs_dict[MonitKey.Used] = fs[1]
                fs_dict[MonitKey.PercentUsed] = fs[2]
                fs_dict[MonitKey.Free] = fs[3]
                fs_dict[MonitKey.PercentFree] = fs[4]
                fs_dict[MonitKey.Mount] = fs[5]

                stats.append(fs_dict.copy())

        except Exception as e:

            logger.error("Could not retrieve file system data.")
            logger.exception(e)

        return stats

    def _get_fs_data(self):

        cmd = ['df', '-hklT']
        fs_data = []

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
                    percent_used = self.calculate_percentage(total, used)

                    available = entry[4]
                    percent_available = self.calculate_percentage(
                        total,
                        available
                    )

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

    def calculate_percentage(self, total, diff):

        if total == 0:
            return 0

        try:

            return str(round(100 * float(diff) / float(total), 2))

        except Exception as e:

            logger.error("Could not calculate percentage.")
            logger.exception(e)

        return 0

    def name(self):
        """Retrieves the name for this plugin.

        Return:

            - The plugin's name.

        """

        return self._name

    def send_results_callback(self, callback):
        """Sets the callback used to send results back to the server.

        Returns:

            - Nothing

        """

        self._send_results = callback

    def register_operation_callback(self, callback):
        """Sets the callback used to register/save operations with the agent
        core.

        Returns:

            - Nothing

        """

        self._register_operation = callback


if __name__ == "__main__":
    print "This plugin is not meant to be run directly. \
        Please run it with the core TopPatch agent."
