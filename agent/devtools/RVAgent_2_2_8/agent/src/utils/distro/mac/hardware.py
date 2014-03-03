import subprocess
import os
import threading
import time

from utils import settings
from utils import logger
from utils.distro.mac import plist

class MacHardware():

    def __init__(self):
        # self.hardware_file = 'hardware.plist'
        # self.hardware_file_path = os.path.join(os.getcwd(), self.hardware_file)
        #
        # try:
        #
        #     output = self.timeout_process()
        #
        #     # Save output of system_profiler to a temp file
        #     file_obj = open(self.hardware_file_path, 'w')
        #     file_obj.write(output)
        #     file_obj.close()
        # except Exception as e:
        #     logger.error("Error reading OSX hardware info.")
        #     logger.exception(e)
        #
        # self.hardware_plist = plist.read_plist(self.hardware_file_path)
        # self._load_hardware_dict()
        #
        # if os.path.exists(self.hardware_file_path):
        #     os.remove(self.hardware_file_path)
        self.plist = plist.PlistInterface()

    def timeout_process(self, data_type):
        """Timeout protection on running system_profiler.

        Have run into issues running system_profiler on OSX. It
        just hangs and never returns thus "freezing" the agent waiting for
        system_profiler output.

        """

        max_tries = 1
        current_try = 0
        timeout = 30  # seconds
        self.process = None
        self.output = ''

        try:

            while current_try < max_tries:

                thread = threading.Thread(target=self.target, args=[data_type])
                thread.daemon = True
                thread.start()

                thread.join(timeout)
                if thread.is_alive():

                    self.process.terminate()
                    thread.join()
                    current_try += 1

                    logger.info("'system_profiler' timed out. "
                                "Current try: %s" % current_try)
                    continue

                return self.output

        except Exception as e:

            logger.error("Unable to run 'system_profiler'.")
            logger.exception(e)
            raise e

        raise Exception(
            "Max tries for system_profiler reached. What's going on?!"
        )

    def target(self, data_type):

        try:

            cmd = ['/usr/sbin/system_profiler', '-xml', data_type]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.output, _err = self.process.communicate()

        except Exception as e:

            logger.error("Unable to run 'system_profiler'."
                         "Waiting for timeout.")
            logger.exception(e)
            while True:
                time.sleep(100)
                pass

        return self.output

    # def _load_hardware_dict(self):
    #     """
    #     Parse the hardware.plist file once and loads needed
    #     data into memory as 'self.hardware' (dict).
    #
    #     Keys:
    #         - cpu
    #         - memory
    #         - display
    #         - ram
    #         - storage
    #         - net
    #
    #     @return: Nothing
    #     """
    #
    #     if self.hardware_plist is None:
    #         self.hardware = None
    #         return
    #
    #     self.hardware = {}
    #     for entry in self.hardware_plist:
    #
    #         if entry['_dataType'] == 'SPHardwareDataType':
    #             self.hardware['cpu'] = entry
    #
    #         elif entry['_dataType'] == 'SPNetworkDataType':
    #             self.hardware['net'] = entry
    #
    #         elif entry['_dataType'] == 'SPMemoryDataType':
    #             self.hardware['memory'] = entry
    #
    #         elif entry['_dataType'] == 'SPDisplaysDataType':
    #             self.hardware['display'] = entry
    #
    #         # storage and scsi types are used for hard drive data.
    #         elif entry['_dataType'] == 'SPStorageDataType':
    #             self.hardware['storage'] = entry
    #
    #         elif entry['_dataType'] == 'SPParallelSCSIDataType':
    #             self.hardware['scsi'] = entry

    def _get_cpu_specs(self):

        cpu_list = []

        output = self.timeout_process('SPHardwareDataType')
        cpu_data = self.plist.read_plist_string(output)

        if len(cpu_data) > 0:
            cpu_data = cpu_data[0]
        else:
            cpu_data = {}

        cpu_id = 1

        try:
            if '_items' in cpu_data:

                for cpu in cpu_data['_items']:
                    cpu_dict = {}

                    # Virtualized OSX might not know the cpu name
                    if 'cpu_type' in cpu:
                        cpu_dict['name'] = cpu['cpu_type']
                    else:
                        cpu_dict['name'] = settings.EmptyValue

                    # system_profiler marks 'packages' as CPU and
                    # 'number_processors' as the number of cores.
                    if 'number_processors' in cpu:
                        cpu_dict['cores'] = str(cpu['number_processors'])
                    else:
                        cpu_dict['cores'] = settings.EmptyValue

                    speed = cpu['current_processor_speed']
                    speed_mhz = settings.EmptyValue
                    if 'GHz'.lower() in speed.lower():
                        speed_digit = speed.split()[0]
                        speed_mhz = float(speed_digit) * 1024

                    cpu_dict['speed_mhz'] = str(speed_mhz)

                    cache_kb = settings.EmptyValue
                    if 'l3_cache' in cpu:
                        cache = cpu['l3_cache']
                        if 'MB'.lower() in cache.lower():
                            cache_digit = cache.split()[0]
                            cache_kb = float(cache_digit) * 1024
                        elif 'KB'.lower() in cache.lower():
                            cache_digit = cache.split()[0]
                            cache_kb = cache_digit

                    cpu_dict['cache_kb'] = str(cache_kb)
                    cpu_dict['bit_type'] = settings.EmptyValue

                    # TODO: Never tested with multiple CPUs. Setting to '1'
                    # Huh?!
                    # expecting 1 CPU.
                    cpu_dict['cpu_id'] = cpu_id
                    cpu_id += 1

                    cpu_list.append(cpu_dict.copy())

        except Exception as e:

            logger.error("Could not retrieve CPU specs.")
            logger.exception(e)

        logger.debug("Done with CPU specs.")
        return cpu_list

    def _get_memory_specs(self):

        # self.hardware['cpu'] is used here because of the 'physical_memory'
        # key. That way we get the total memory.
        total_ram = settings.EmptyValue

        output = self.timeout_process('SPHardwareDataType')
        memory_data = self.plist.read_plist_string(output)

        if len(memory_data) > 0:
            memory_data = memory_data[0]
        else:
            memory_data = {}

        try:

            # Memory RAM data
            if '_items' in memory_data:
                for entry in memory_data['_items']:
                    if 'physical_memory' in entry:

                        memory = entry['physical_memory']
                        size_kb = settings.EmptyValue

                        if 'GB'.lower() in memory.lower():
                            size_digit = memory.split()[0]
                            # 1 GB == 1048576 kB
                            size_kb = float(size_digit) * 1048576

                        elif 'MB'.lower() in memory.lower():
                            size_digit = memory.split()[0]
                            # 1 MB == 1024 kB
                            size_kb = float(size_digit) * 1024

                        total_ram  = size_kb
                        break

        except Exception as e:

            logger.error("Could not retrieve memory specs.")
            logger.exception(e)

        logger.debug("Done with memory specs.")
        return str(total_ram)

    def _get_display_specs(self):
        # Display (video card) data
        display_list = []

        output = self.timeout_process('SPDisplaysDataType')
        display_data = self.plist.read_plist_string(output)

        if len(display_data) > 0:
            display_data = display_data[0]
        else:
            display_data = {}

        try:

            if '_items' in display_data:
                for display in display_data['_items']:
                    display_dict = {}

                    # Virtualized OSX might not know the gpu name
                    if 'sppci_model' in display:
                        display_dict['name'] = display['sppci_model']
                    else:
                        display_dict['name'] = settings.EmptyValue

                    # As of now, speed is not known to system_profiler
                    display_dict['speed_mhz'] = settings.EmptyValue

                    ram = display['spdisplays_vram']
                    ram_kb = settings.EmptyValue
                    if "MB".lower() in ram.lower():
                        ram_digit = ram.split()[0]
                        # 1 MB == 1024 kB
                        ram_kb = float(ram_digit) * 1024
                    display_dict['ram_kb'] = ram_kb

                    display_list.append(display_dict.copy())

        except Exception as e:

            logger.error("Could not retrieve display specs.")
            logger.exception(e)


        logger.debug("Done with display specs.")
        return display_list

    def _get_hd_specs(self):
        # Hard drive (storage) data
        hdd_list = []

        try:

            fs_data = self._filesystem_usage()

            for hdd in fs_data:
                hdd_dict = {}

                hdd_dict['name'] = hdd[0]
                hdd_dict['free_size_kb'] = hdd[2]
                hdd_dict['size_kb'] = hdd[3]
                hdd_dict['file_system'] = self._filesystem_type(hdd[0])

                hdd_list.append(hdd_dict)

        except Exception as e:

            logger.error("Could not retrieve hard drive specs.")
            logger.exception(e)

        logger.debug("Done with file system specs.")
        return hdd_list

    def _filesystem_type(self, name=''):

        fs_type = ''

        try:

            process = subprocess.Popen(['mount'], stdout=subprocess.PIPE)
            output, _error = process.communicate()

            for line in output.splitlines():

                if line.startswith(name):

                    out = line.split('(')
                    if len(out) > 1:

                        out = out[1].split(',')
                        if len(out) > 0:

                            fs_type = out[0]
                            break

        except Exception as e:

            logger.error("Could not retrieve hard drive specs.")
            logger.exception(e)

        return fs_type


    def _filesystem_usage(self):

        _ignore_keywords = ['map', 'Filesystem', 'devfs', 'tempfs', '-hosts',
                            'auto_home']

        outlines = []

        process = subprocess.Popen(['df', '-kl'], stdout=subprocess.PIPE)
        output, _error = process.communicate()

        # Nifty way to remove all the spaces in the output.
        for line in output.splitlines():
            outlines.append([x for x in line.split(' ') if x != ''])

        fs_data = []
        for line in outlines:

            name = ''
            used = 0
            available = 0
            mount = ''

            if line[0] in _ignore_keywords:
                continue

            for i in range(len(line)):

                # Try to convert string to a number. Fails to, then its a
                # string string!
                if not self._try_long_cast(line[i]):
                    name = "%s %s" % (name, line[i])
                    name = name.strip()
                    continue

                # + n to skip over the 'blocks' digit
                used = long(line[i + 1])
                available = long(line[i + 2])
                mount = line[i + 4]

                break

            fs_data.append(
                (
                    name,
                    str(used),
                    str(available),
                    str(used + available),
                    mount
                )
            )

        return fs_data

    def _try_long_cast(self, string):
        """Wrapper to cast a string into a long. No try/except all over the place.
        Returns:

            (bool) True if cast is successful. False otherwise.
        """
        try:
            long(string)
            return True
        except ValueError:
            return False

    def _parse_volumes(self, item):
        """
        Parse the volume item returning a list of interested partitions.
        @param item: Root '_item" under the "SCSI Parallel Domain". Wordplay
        courtesy system_profiler.
        @return: List of partitions.
        """
        hdd_list = []

        try:

            if 'volumes' in item:
                for volume in item['volumes']:
                    if 'file_system' in volume:
                        hdd_dict = {}

                        if  '_name' in volume:
                            hdd_dict['name'] = volume['_name']
                        else:
                            hdd_dict['name'] = settings.EmptyValue

                        if 'size_in_bytes' in volume:
                            hdd_dict['size_kb'] = volume['size_in_bytes'] / 1024
                        else:
                            hdd_dict['size_kb'] = 0

                        if 'free_space_in_bytes' in volume:
                            hdd_dict['free_size_kb'] = (
                                volume['free_space_in_bytes'] / 1024)
                        else:
                            hdd_dict['free_size_kb'] = 0

                        if 'file_system' in volume:
                            hdd_dict['file_system'] = volume['file_system']
                        else:
                            hdd_dict['file_system'] = settings.EmptyValue

                        hdd_list.append(hdd_dict.copy())

        except Exception as e:

            logger.error("Could not parse volumes.")
            logger.exception(e)

        return hdd_list

    def _get_nic_specs(self):
        # Network interface data
        nic_list = []

        output = self.timeout_process('SPNetworkDataType')
        net = self.plist.read_plist_string(output)

        if len(net) > 0:
            net = net[0]
        else:
            net = {}

        try:
            if '_items' in net:

                for nic in net['_items']:

                    nic_data = {}

                    if 'Ethernet' in nic:

                        nic_data['name'] = (
                            "%s (%s)" % (nic['_name'], nic['interface'])
                        )

                        ethernet = nic['Ethernet']
                        if 'MAC Address' in ethernet:

                            nic_data['mac'] = (
                                ethernet['MAC Address'].replace(':', '')
                            )

                        else:

                            nic_data['mac'] = settings.EmptyValue


                        if 'ip_address' in nic:

                            nic_data['ip_address'] = nic['ip_address'][0]

                        else:

                            nic_data['ip_address'] = settings.EmptyValue

                        nic_list.append(nic_data.copy())

        except Exception as e:

            logger.error("Could not retrieve NIC specs.")
            logger.exception(e)

        logger.debug("Done with NIC specs.")
        return nic_list

    def get_specs(self):
        return {
            'cpu': self._get_cpu_specs(),
            'memory': self._get_memory_specs(),
            'display': self._get_display_specs(),
            'storage': self._get_hd_specs(),
            'nic': self._get_nic_specs(),
            }

    def empty_specs(self):
        return {
            'cpu': "",
            'memory': "",
            'display': "",
            'storage': "",
            'nic': "",
            }
