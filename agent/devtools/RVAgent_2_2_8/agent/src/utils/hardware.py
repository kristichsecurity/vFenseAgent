import subprocess
import re
import platform

from distro.mac.hardware import MacHardware
from utils import settings
from utils import logger


def get_hw_info():
    """ This method basically just calls the respected hardware class
    to get the specs.
    """
    
    hw_info = {}

    if platform.system() == "Darwin":
        hw_info = MacHardware().get_specs()
    else:
        hw_info['cpu'] = CpuInfo().get_cpu_list()
        hw_info['memory'] = get_total_ram()
        hw_info['display'] = DisplayInfo().get_display_list()
        hw_info['storage'] = HarddriveInfo().get_hdd_list()
        hw_info['nic'] = NicInfo().get_nic_list()

    format_hw_info(hw_info)

    return hw_info

def format_hw_info(hw_dict):
    # CPU info
    for cpu in hw_dict['cpu']:
        if cpu['cpu_id']:
            cpu['cpu_id'] = int(cpu['cpu_id'])

        if cpu['bit_type']:
            cpu['bit_type'] = int(cpu['bit_type'])

        if cpu['speed_mhz']:
            cpu['speed_mhz'] = float(cpu['speed_mhz'])

        if cpu['cores']:
            cpu['cores'] = int(cpu['cores'])

        if cpu['cache_kb']:
            cpu['cache_kb'] = float(cpu['cache_kb'])

    # Memory info
    hw_dict['memory'] = float(hw_dict['memory'])

    # Display info
    for display in hw_dict['display']:
        display['ram_kb'] = int(display['ram_kb'])

    # Storage info
    for hdd in hw_dict['storage']:
        hdd['free_size_kb'] = int(hdd['free_size_kb'])
        hdd['size_kb'] = int(hdd['size_kb'])

def empty_specs():
    """
    Simple way to create empty hardware list.
    @return: empty HW list
    """
    return {
        'cpu': [],
        'memory': "",
        'display': [],
        'storage': [],
        'nic': [],
        }


class CpuInfo():

    def __init__(self):

        try:
            cmd = ['cat', '/proc/cpuinfo']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            self._raw_output, _stderr = process.communicate()
            self._parse_output()
            self._load_data()
        except Exception as e:
            logger.error("Error reading cpu info.")
            logger.exception(e)
            self._cpus = {} # Something went wrong, set to empty dict.

    def _load_data(self):
        self._physical_ids = {}
        self._cpus = {}

        for logical_cpu in self._logical_cpu_list:
            _id = logical_cpu["physical_id"]
            name = logical_cpu["name"]
            self._physical_ids[_id] = name

        self._number_of_cpus = len(self._physical_ids)

        for i in range(self._number_of_cpus):
            for logical_cpu in self._logical_cpu_list:
                p_id = logical_cpu["physical_id"]

                if p_id in self._cpus:
                    continue

                logical_dict = self._create_physical_dict(
                    str(i),
                    logical_cpu["name"],
                    logical_cpu["cores"],
                    logical_cpu["speed_mhz"],
                    logical_cpu["cache_kb"],
                    logical_cpu["bit_type"]
                )

                self._cpus[p_id] = logical_dict.copy()

    def _parse_output(self):
        self._cat_output = []
        for s in self._raw_output.splitlines():
            self._cat_output.append(s.replace("\t", ''))

        self._logical_cpu_list = []

        # Setting the physical id to zero in the event that there is
        # only one physical CPU. /proc/cpuinfo doesn't display 'physical id'
        # and 'core id' if there is only one.
        self._cpu_dict = {}
        self._cpu_dict["physical_id"] = '0'
        self._cpu_dict["cores"] = '0'

        for entry in self._cat_output:

            if entry.find('processor: ') == 0:

                logical_id = entry.partition(":")[2].strip()
                self._cpu_dict["processor"] = logical_id

                continue

            elif entry.find('physical id:') == 0:

                physical_id = entry.partition(":")[2].strip()
                self._cpu_dict["physical_id"] = physical_id

                continue

            elif entry.find('core id:') == 0:

                core_id = entry.partition(":")[2].strip()
                self._cpu_dict["core_id"] = core_id

                continue

            elif entry.find('cpu cores:') == 0:

                cores = entry.partition(":")[2].strip()
                self._cpu_dict["cores"] = cores

                continue

            elif entry.find('model name:') == 0:

                model_name = entry.partition(":")[2].strip()
                self._cpu_dict["name"] = model_name

                continue

            elif entry.find('cpu MHz:') == 0:

                speed = entry.partition(":")[2].strip()
                self._cpu_dict["speed_mhz"] = speed

                continue

            elif entry.find('cache size:') == 0:

                size = entry.partition(":")[2].strip()

                size_kb = settings.EmptyValue
                if "KB".lower() in size.lower():
                    # Some logic here!!
                    size_kb = size.lower().replace("KB".lower(), "").strip()

                self._cpu_dict["cache_kb"] = size_kb

                continue

            # 'flags' show a lot of options on one line separated by a space.
            elif entry.find('flags:') == 0:

                # lm is the flag set by linux to indicate 64bit
                # X86_FEATURE_LM (long mode)
                if " lm " in entry:
                    self._cpu_dict["bit_type"] = '64'
                else:
                    self._cpu_dict["bit_type"] = '32'

                continue

            # Empty line means the beginning of a new processor item. Save.
            elif entry == "":
                self._logical_cpu_list.append(self._cpu_dict.copy())

        # just some clean up.
        self._cpu_dict = None

    def _create_physical_dict(self, _id,
                              name='',
                              cores='',
                              speed_mhz='',
                              cache_kb='',
                              bit_type=''):

        logical_dict = {}
        logical_dict["cpu_id"] = _id
        logical_dict["name"] = name
        logical_dict["cores"] = cores
        logical_dict["speed_mhz"] = speed_mhz
        logical_dict["cache_kb"] = cache_kb
        logical_dict["bit_type"] = bit_type

        return logical_dict

    def get_cpu_list(self):
        cpu_list = []

        for cpu in self._cpus:
            cpu_list.append(self._cpus[cpu])

        return cpu_list


class DisplayInfo():

    def __init__(self):

        try:
            cmd = ['lspci', '-v']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            self._raw_output, _ = process.communicate()
            self._parse_output()
        except Exception as e:
            logger.error("Error reading display info.")
            logger.exception(e)
            self._display_list = [] # Something went wrong, set to empty list.

    def _parse_output(self):
        tmp_list = []
        for s in self._raw_output.splitlines():
            tmp_list.append(s.replace("\t", ''))

        self._output = tmp_list
        self._display_dict = None

        self._display_list = []

        reading_vga = False
        for entry in self._output:

            if 'VGA compatible controller: ' in entry:

                name = entry.partition('VGA compatible controller:')[2].strip()
                self._display_dict = {"name" : name}

                reading_vga = True

                continue

            elif (entry.find('Flags: ') == 0) and reading_vga:

                flags = entry.partition(":")[2].strip()
                match = re.match(r'[0-9]+MHz', flags)

                speed_mhz = settings.EmptyValue
                if match:
                    speed_mhz = match.group().split('MHz')[0]

                self._display_dict["speed_mhz"] = speed_mhz

                continue

            elif (entry.find('Memory at ') == 0)\
                 and ("prefetchable" in entry) and reading_vga:

                size_string = entry.split("[size=")[1].replace(']','')

                size_kb = settings.EmptyValue
                # MB
                if "M" in size_string:
                    size = int(size_string.replace('M', ''))
                    size_kb = size * 1024

                    # GB
                elif "G" in size_string:
                    size = int(size_string.replace('G', ''))
                    size_kb = (size * 1024) * 1024

                self._display_dict["ram_kb"] = str(size_kb)

                continue

            # Empty line means the beginning of a new processor item. Save.
            elif entry == "" and reading_vga:
                self._display_list.append(self._display_dict.copy())
                reading_vga = False

    def get_display_list(self):
        return self._display_list


class HarddriveInfo():

    def __init__(self):

        self._hdd_list = []

        try:
            # df options:
            # 'h': print sizes in human readable format ('k' = KB)
            # 'l': local file systems. 'T': file system type (ext3/ext4/db)
            cmd = ['df', '-hklT']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            self._raw_output, _stderr = process.communicate()
            self._parse_output()
        except Exception as e:
            logger.error("Error reading hard drive info.", 'error')
            logger.exception(e)
            self._hdd_list = []  # Something went wrong, set to empty list.

    def _parse_output(self):
        self._output = []
        for line in self._raw_output.splitlines():
            self._output.append([x for x in line.split(' ') if x != ''])

        _partition_blacklist = [
            'tmpfs',
            'rootfs',
            'none',
            'devtmpfs',
            'Filesystem'
        ]

        tmp_dict = {}
        for entry in self._output:

            if entry[0] in _partition_blacklist:
                continue

            # An ideal entry would consist of 7 items. It would look like:
            # ['/dev/sda1', 'ext4', '495844', '38218', '432026', '9%', '/boot']
            if len(entry) == 7:
                tmp_dict['name'] = entry[0]

                tmp_dict['size_kb'] = int(entry[3]) + int(entry[4])
                tmp_dict['free_size_kb'] = entry[4]
                tmp_dict['file_system'] = entry[1]
            else:
                # But less then 7 items means the name of the partition and its
                # data were split across two entries:
                # ['/dev/mapper/vg_centosmon-lv_root'],
                # ['ext4', '12004544', '3085772', '8796828', '26%', '/']
                # Taking that into consideration here.
                if len(entry) == 1:
                    tmp_dict['name'] = entry[0]
                    continue
                elif len(entry) == 6:
                    tmp_dict['size_kb'] = int(entry[2]) + int(entry[3])
                    tmp_dict['free_size_kb'] = entry[3]
                    tmp_dict['file_system'] = entry[0]

            self._hdd_list.append(tmp_dict.copy())

    def get_hdd_list(self):
        return self._hdd_list


class NicInfo():

    def __init__(self):

        self._nics = []

        try:
            cmd = ['ip', 'addr']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            self._raw_output, _stderr = process.communicate()
            self._parse_output()
        except Exception as e:
            logger.error("Error reading nic info.", 'error')
            logger.exception(e)
            self._nics = []  # Something went wrong, set to empty dict.

    def _parse_output(self):
        self._output = [line.strip() for line in self._raw_output.splitlines()]

        #### Inserting a '\n' between interfaces. Easier to parse...
        indices = []
        for i in range(len(self._output)):
            match = re.match(r'[0-9]+:', self._output[i])
            if match:
                if i > 1:
                    indices.append(i)

        for i in indices:
            self._output.insert(i, '')

        self._output.insert(len(self._output), '')
        #######################################################

        reading_flag = False
        temp_dict = {}
        for entry in self._output:

            match = re.match(r'[0-9]+:', entry)
            if match:
                temp_dict = {}

                iface_num = match.group()
                new_entry = entry.replace(iface_num, '').strip()

                reading_flag = True
                temp_dict['name'] = new_entry.partition(':')[0]

                continue

            elif entry.find('link/loopback') == 0:
                reading_flag = False
                temp_dict = {}
                continue

            elif entry.find('link/ether') == 0 and reading_flag:

                mac = entry.replace('link/ether', ''
                ).partition('brd')[0].strip()

                mac = mac.replace(':', '') # Server doesn't expect ':'s
                temp_dict['mac'] = mac

            # Space after 'inet' to prevent check with 'inet6'
            elif entry.find('inet ') == 0 and reading_flag:

                ip = entry.replace('inet ', '').partition('/')[0].strip()
                temp_dict['ip_address'] = ip

            elif entry == "" and reading_flag:
                reading_flag = False
                self._nics.append(temp_dict.copy())


    def get_nic_list(self):

        return self._nics


def get_total_ram():

    try:
        cmd = ['cat', '/proc/meminfo']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        _raw_output, _stderr = process.communicate()

        total_output = _raw_output.splitlines()[0]
        mem = total_output.partition(":")[2].split(" ")[-2]

    except Exception as e:
        logger.error("Error reading memory info.", 'error')
        logger.exception(e)
        mem = settings.EmptyValue

    return mem
