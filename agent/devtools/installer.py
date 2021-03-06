#!/usr/bin/python

import os
import sys
import time
import shutil
import urllib2
import platform
import datetime
import traceback
import subprocess
import ConfigParser

from optparse import OptionParser

# Should be set at agent build time
COMPILED_PYTHON_BIT_TYPE = ''

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

OPT_DIR = '/opt'
AGENT_DIR = 'agent'
UPDATE_FILE = '.agent_update'
TOPPATCH_DIR = os.path.join(OPT_DIR, 'TopPatch')
AGENT_PATH = os.path.join(TOPPATCH_DIR, AGENT_DIR)
AGENT_CONFIG = os.path.join(AGENT_PATH, 'agent.config')
UPDATE_LOG = os.path.join(TOPPATCH_DIR, 'tmp', 'TopPatchAgentUpdate.log')
INSTALL_LOG = os.path.join(TOPPATCH_DIR, 'agent_install_failure.log')

AGENT_TMP_LOCATION = os.path.join(TOPPATCH_DIR, 'tmp')

MAC_PYTHON_EXE = \
    os.path.join(AGENT_PATH, 'deps', 'mac', 'Python-2.7.5', 'bin', 'python')
RPM_PYTHON_EXE = \
    os.path.join(AGENT_PATH, 'deps', 'rpm', 'Python-2.7.5', 'bin', 'python')
RPM6_PYTHON_EXE = \
    os.path.join(AGENT_PATH, 'deps', 'rpm6', 'Python-2.7.5', 'bin', 'python')
RPM_32_PYTHON_EXE = \
    os.path.join(AGENT_PATH, 'deps', 'rpm-32', 'Python-2.7.5', 'bin', 'python')
RPM6_32_PYTHON_EXE = \
    os.path.join(AGENT_PATH, 'deps', 'rpm6-32', 'Python-2.7.5', 'bin',
                 'python')
DEB_PYTHON_EXE = \
    os.path.join(AGENT_PATH, 'deps', 'deb', 'Python-2.7.5', 'bin', 'python')

PYTHON_BIN_EXE = os.path.join(AGENT_PATH, 'bin', 'python')

APP_SETTINGS_SECTION = 'appSettings'
AGENT_INFO_SECTION = 'agentInfo'

RPM_DISTROS = [
    'fedora', 'centos', 'centos linux', 'red hat enterprise linux server'
]
DEBIAN_DISTROS = ['debian', 'ubuntu', 'linuxmint']


# Defaults when option is not provided to this install script
default_options = {'agentid': '',
                   'nu': '',
                   'wp': '',
                   'serverhostname': '',
                   'serveripaddress': '',
                   'customer': 'default',
                   'serverport': '443',
                   'agentport': '9003',
                   'starterport': '9005',
                   'tunnelport': '22',
                   'loglevel': 'debug'}


def run_command(cmd):
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    result, err = proc.communicate()

    return result, err


def create_necessary_dirs():
    if not os.path.exists(OPT_DIR):
        os.makedirs(OPT_DIR)

    if not os.path.exists(TOPPATCH_DIR):
        os.makedirs(TOPPATCH_DIR)


def write_log(file_path, error):
    f = open(file_path, 'a')

    try:
        f.write("%s : %s" % (str(datetime.datetime.now()), str(error)))
        f.write(os.linesep)
    finally:
        f.close()


def write_update_log(message):
    # Will throw an exception if full path cannot be reached due to missing
    # directories.
    write_log(UPDATE_LOG, message)


def write_install_log(message):
    create_necessary_dirs()
    write_log(INSTALL_LOG, message)


def get_date():
    return time.strftime('%m/%d/%Y')


def write_config(config_path, args):
    read_config = ConfigParser.SafeConfigParser()
    write_config = ConfigParser.SafeConfigParser()

    read_config.read(config_path)
    AgentName = read_config.get(AGENT_INFO_SECTION, 'name')
    AgentVersion = read_config.get(AGENT_INFO_SECTION, 'version')
    AgentDescription = read_config.get(AGENT_INFO_SECTION, 'description')

    write_config.add_section(APP_SETTINGS_SECTION)
    write_config.set(APP_SETTINGS_SECTION, 'agentid', args.agentid)
    write_config.set(APP_SETTINGS_SECTION, 'nu', args.username)
    write_config.set(APP_SETTINGS_SECTION, 'wp', args.password)
    write_config.set(
        APP_SETTINGS_SECTION, 'serverhostname', args.serverhostname
    )
    write_config.set(
        APP_SETTINGS_SECTION, 'serveripaddress', args.serveripaddress
    )
    write_config.set(APP_SETTINGS_SECTION, 'serverport', args.serverport)
    write_config.set(APP_SETTINGS_SECTION, 'agentport', args.agentport)
    write_config.set(APP_SETTINGS_SECTION, 'tunnelport', args.tunnelport)
    write_config.set(APP_SETTINGS_SECTION, 'loglevel', args.loglevel)
    write_config.set(APP_SETTINGS_SECTION, 'customer', args.customer)

    write_config.add_section(AGENT_INFO_SECTION)
    write_config.set(AGENT_INFO_SECTION, 'name', AgentName)
    write_config.set(AGENT_INFO_SECTION, 'version', AgentVersion)
    write_config.set(AGENT_INFO_SECTION, 'description', AgentDescription)
    write_config.set(AGENT_INFO_SECTION, 'installdate', get_date())

    f = open(config_path, 'w')

    try:
        write_config.write(f)
    finally:
        f.close()


def get_config_option(config_reader, section, option):
    default = default_options[option]

    try:
        config_option = config_reader.get(section, option)
        return config_option
    except Exception:
        return default


def update_config(args, new_agent_path):

    if '.app' in args.old_agent_path:
        old_config = os.path.join(
            args.old_agent_path, 'Contents', 'Resources', 'agent.config'
        )
    else:
        old_config = os.path.join(args.old_agent_path, 'agent.config')

    read_old_config = ConfigParser.SafeConfigParser()
    read_old_config.read(old_config)

    agentid = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'agentid'
    )

    username = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'nu'
    )

    password = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'wp'
    )

    serverhostname = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'serverhostname'
    )

    serveripaddress = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'serveripaddress'
    )

    serverport = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'serverport'
    )

    starterport = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'starterport'
    )

    tunnelport = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'tunnelport'
    )

    agentport = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'agentport'
    )

    loglevel = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'loglevel'
    )

    customer = get_config_option(
        read_old_config, APP_SETTINGS_SECTION, 'customer'
    )

    if args.agentid:
        agentid = args.agentid

    if args.username:
        username = args.username

    if args.password:
        password = args.password

    if args.serverhostname:
        serverhostname = args.serverhostname

    if args.serveripaddress:
        serveripaddress = args.serveripaddress

    if args.serverport:
        serverport = args.serverport

    if args.starterport:
        starterport = args.starterport

    if args.tunnelport:
        tunnelport = args.tunnelport

    if args.agentport:
        agentport = args.agentport

    if args.loglevel:
        loglevel = args.loglevel

    if args.customer:
        customer = args.customer

    # Grab the agentInfo of the new config
    new_config = os.path.join(new_agent_path, 'agent.config')
    read_new_config = ConfigParser.SafeConfigParser()
    read_new_config.read(new_config)

    name = read_new_config.get(AGENT_INFO_SECTION, 'name')
    version = read_new_config.get(AGENT_INFO_SECTION, 'version')
    description = read_new_config.get(AGENT_INFO_SECTION, 'description')

    write_config = ConfigParser.SafeConfigParser()
    write_config.add_section(APP_SETTINGS_SECTION)
    write_config.set(APP_SETTINGS_SECTION, 'agentid', agentid)
    write_config.set(APP_SETTINGS_SECTION, 'nu', username)
    write_config.set(APP_SETTINGS_SECTION, 'wp', password)
    write_config.set(APP_SETTINGS_SECTION, 'serverhostname', serverhostname)
    write_config.set(APP_SETTINGS_SECTION, 'serveripaddress', serveripaddress)
    write_config.set(APP_SETTINGS_SECTION, 'serverport', serverport)
    write_config.set(APP_SETTINGS_SECTION, 'starterport', starterport)
    write_config.set(APP_SETTINGS_SECTION, 'tunnelport', tunnelport)
    write_config.set(APP_SETTINGS_SECTION, 'agentport', agentport)
    write_config.set(APP_SETTINGS_SECTION, 'loglevel', loglevel)
    write_config.set(APP_SETTINGS_SECTION, 'customer', customer)

    write_config.add_section(AGENT_INFO_SECTION)
    write_config.set(AGENT_INFO_SECTION, 'name', name)
    write_config.set(AGENT_INFO_SECTION, 'version', version)
    write_config.set(AGENT_INFO_SECTION, 'description', description)
    write_config.set(AGENT_INFO_SECTION, 'installdate', get_date())

    f = open(new_config, 'w')

    try:
        write_config.write(f)
    finally:
        f.close()


def create_symlink(symlink_target, symlink_path):
    cmd = ['/bin/ln', '-s', symlink_target, symlink_path]
    result, err = run_command(cmd)

    if err:
        raise Exception(err)


def delete_directory(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def dict_to_json(dictionary):
    """
    Basic dictionary to JSON converter. Does not check types, turns
    everything into a string on json.
    """
    json = []

    json.append("{")

    for k in dictionary:
        json.append('"' + k + '"')
        json.append(':')
        json.append('"' + dictionary[k] + '"')
        json.append(',')

    # Change the last comma to a closing brace
    json[-1] = "}"

    return ''.join(json)


def write_operation_success(app_id, operation_id, success, path):
    root = {}
    root['app_id'] = app_id
    root['operation_id'] = operation_id
    root['success'] = success

    json = dict_to_json(root)

    write_update_log(json)

    f = open(path, 'w')

    try:
        f.write(json)
    finally:
        f.close()


def printErrors(errors):
    print "Error(s):"

    for e in errors:
        print "    %s" % e

    sys.exit(1)


def verify_credentials(username, password, server_address):
    """
    Returns message corresponding to error code, if any. If an unknown error
    occured, it will pass the exception. Returns empty string on a 200.
    """
    known_errors = {
        403: 'Invalid username/password.',
        500: 'Internal server error.'
    }

    url = "https://%s/rvl/login" % server_address

    data = {}
    data['name'] = username
    data['password'] = password

    data_json = dict_to_json(data)
    #data_json = '{"name":"admin", "password":"toppatch"}'

    req = urllib2.Request(
        url, data_json, {'Content-Type': 'application/json'}
    )

    try:
        f = urllib2.urlopen(req)
        f.close()
    except urllib2.HTTPError, e:
        if e.code in known_errors:
            return known_errors[e.code]
        else:
            raise e

    return ''


def check_user_input(args):
    errors = []

    if not args.username or not args.password:
        errors.append(
            ("Please provide both username and password to -u and -p "
             "respectively.")
        )

    if not args.serverhostname and not args.serveripaddress:
        errors.append(
            'Please provide server hostname to -s or serveripaddress to -i.'
        )

    if args.serverhostname:
        server_address = args.serverhostname
    else:
        server_address = args.serveripaddress

    cred_err = verify_credentials(args.username, args.password, server_address)

    if cred_err:
        errors.append(cred_err)

    if errors:
        printErrors(errors)


class MacInstaller():
    def __init__(self):
        self.system_daemon_path = '/Library/LaunchDaemons'
        self.daemon_plist_name = 'com.toppatch.agent.plist'
        self.system_plist = os.path.join(
            self.system_daemon_path, self.daemon_plist_name
        )

    def _unload_plist(self, path):
        cmd = ['/bin/launchctl', 'unload', path]
        result, err = run_command(cmd)

        return True

    def _remove_running_plist(self):
        try:
            if os.path.exists(self.system_plist):
                self._unload_plist(self.system_plist)
                # TODO: no need to delete, since the install overwrites?
        except Exception:
            write_install_log('Failed to remove running agent.')

    def _load_plist(self, path):
        cmd = ['/bin/launchctl', 'load', '-w', path]
        result, err = run_command(cmd)

        if err:
            raise Exception(err)

    def install(self, args):
        check_user_input(args)

        try:
            self._remove_running_plist()

            if os.path.exists(AGENT_PATH):
                shutil.rmtree(AGENT_PATH)

            # Move the agent
            shutil.copytree(
                os.path.join(CURRENT_DIR, AGENT_DIR), AGENT_PATH
            )

            # write to agent.config
            write_config(AGENT_CONFIG, args)

            # Copy agent plist to system, this also overwrites
            agent_plist_path = os.path.join(
                AGENT_PATH, 'daemon', 'mac', self.daemon_plist_name
            )
            shutil.copy(agent_plist_path, self.system_daemon_path)

            # Create symlink to corresponding compiled python
            create_symlink(MAC_PYTHON_EXE, PYTHON_BIN_EXE)

            # Run agent's plist
            self._load_plist(
                os.path.join(self.system_daemon_path, self.daemon_plist_name)
            )

        except Exception, e:
            write_install_log(e)
            write_install_log(traceback.format_exc())

    def _overwrite_system_daemon_plist(self, agent_path):
        plist_path = os.path.join('daemon', 'mac', self.daemon_plist_name)
        shutil.copy(os.path.join(agent_path, plist_path), self.system_plist)

    def eject_dmg(self, mount_point):
        """Ejects the mount point give.

        Args:

            - mount_point: Mount point to eject. (ie: /Volumes/Image.dmg)

        Returns:

            - True if ejected successfully; False otherwise.
        """

        cmd = ['/usr/bin/hdiutil', 'detach', '-force', mount_point]
        ejected = False

        try:

            raw_output, _ = run_command(cmd)

            error_message = ''

            for line in raw_output.splitlines():

                if 'ejected' in line:

                    ejected = True
                    break

                else:

                    error_message += line

        except Exception, e:
            raise Exception(e)

        return ejected

    def update(self, args):
        tmp_agent_path = os.path.join(AGENT_TMP_LOCATION, AGENT_DIR)

        try:
            create_necessary_dirs()

            if not os.path.exists(AGENT_TMP_LOCATION):
                os.makedirs(AGENT_TMP_LOCATION)

            # Unload old agent plist
            self._unload_plist(self.system_plist)
            write_update_log("Unloaded old daemon process.")

            # Move the applciation from image to temporary folder.
            # Allows copying over old config without deleting old agent, yet.
            delete_directory(tmp_agent_path)  # delete if already exists
            shutil.copytree(
                os.path.join(CURRENT_DIR, AGENT_DIR), tmp_agent_path
            )
            write_update_log("Copied the new agent to tmp directory.")

            update_config(args, tmp_agent_path)
            write_update_log("Copied/updated old config file.")

            vine_settings = os.path.join(
                args.old_agent_path, 'etc', '.vinesettings'
            )
            if os.path.exists(vine_settings):
                tmp_etc = os.path.join(tmp_agent_path, 'etc')

                if not os.path.exists(tmp_etc):
                    os.makedirs(tmp_etc)

                tmp_vnc_path = os.path.join(tmp_etc, '.vinesettings')

                # If it exists, copy it over to the new agent.
                shutil.copy(vine_settings, tmp_vnc_path)

            self._overwrite_system_daemon_plist(tmp_agent_path)
            write_update_log("Agent plist has been overwritten.")

            delete_directory(args.old_agent_path)
            write_update_log("Deleted old agent.")

            shutil.move(tmp_agent_path, AGENT_PATH)
            write_update_log("Moved new agent to /opt directory.")

            create_symlink(MAC_PYTHON_EXE, PYTHON_BIN_EXE)
            write_update_log("Created symlink.")

            self._load_plist(self.system_plist)
            write_update_log("Loaded plist.")

            # TODO: Improve the message passing between old and new agent.
            # Passing appid and operationid as arguments doesn't seem right.
            write_update_log("{0} , {1}".format(args.appid, args.operationid))
            if args.appid and args.operationid:
                etc_path = os.path.join(AGENT_PATH, 'etc')
                success = 'true'

                write_update_log("etc_path: {0}".format(etc_path))

                if not os.path.exists(etc_path):
                    os.makedirs(etc_path)

                update_file = os.path.join(etc_path, UPDATE_FILE)

                write_update_log("update_file: {0}".format(update_file))

                write_operation_success(
                    args.appid, args.operationid, success, update_file
                )

            # Clean up
            #shutil.rmtree(self.tmp_location)
            write_update_log("current_dir: {0}".format(CURRENT_DIR))

            # Change directory so that the dmg this is living in can be
            # unmounted.
            os.chdir('/opt')
            self.eject_dmg(CURRENT_DIR)

        except Exception, e:
            write_update_log(e)
            write_update_log(traceback.format_exc())

            try:
                delete_directory(tmp_agent_path)
            except Exception, e2:
                write_update_log("Failed to remove tmp agent.")
                write_update_log(e2)
                write_update_log(traceback.format_exc())

            self.eject_dmg(CURRENT_DIR)


class RpmInstaller:
    pass


class DebInstaller:
    pass


###################################################################
###################################################################
###################################################################

def get_platform():
    return platform.system().lower()


def get_distro():
    plat = get_platform()

    if plat == 'darwin':
        return 'darwin'

    elif plat == 'linux':
        return platform.linux_distribution()[0].lower()

    return ''


def get_installer():
    distro = get_distro()

    if distro == 'darwin':
        return MacInstaller()

    elif distro in RPM_DISTROS:
        return RpmInstaller()

    elif distro in DEBIAN_DISTROS:
        return DebInstaller()


def check_privilege():
    """
    Checks for sudo privileges. Exits if it does not have sudo privileges.
    """
    if os.geteuid() != 0:
        sys.exit("install script must be run as root.")


def check_bit_type():
    """
    Compares system bit type with the compiled python bit type. Exits
    on conflict.
    """
    sys_arch = platform.architecture()[0]

    if COMPILED_PYTHON_BIT_TYPE != sys_arch:
        sys.exit(
            ("This system appears to be {0}, but the agent is {1}."
             " Please install the {0} agent."
             .format(sys_arch, COMPILED_PYTHON_BIT_TYPE))
        )


def get_input():
    """
    Gets the input from options passed into the install script.
    """
    parser = OptionParser()

    parser.add_option("-u", "--username", dest="username",
                      default=default_options['nu'], help="This is required.")
    parser.add_option("-p", "--password", dest="password",
                      default=default_options['wp'], help="This is required.")
    parser.add_option(
        "-s", "--serverhostname", default=default_options['serverhostname'],
        dest="serverhostname",
        help=("Please provide server hostname and/or server ip address."
              " Only one required.")
    )
    parser.add_option(
        "-i", "--serveripaddress", default=default_options['serveripaddress'],
        dest="serveripaddress",
        help=("Please provide server ip address and/or server hostname."
              " Only one required.")
    )
    parser.add_option("-c", "--customer", default=default_options['customer'],
                      dest="customer", help="Default: default.")
    parser.add_option("--serverport", default=default_options['serverport'],
                      dest="serverport", help="Default: 443.")
    parser.add_option("--agentport", default=default_options['agentport'],
                      dest="agentport", help="Default: 9003.")
    parser.add_option("--starterport", default=default_options['starterport'],
                      dest="starterport", help="Default: 9005.")
    parser.add_option("--tunnelport", default=default_options['tunnelport'],
                      dest="tunnelport", help="Default: 22.")
    parser.add_option("--loglevel", default=default_options['loglevel'],
                      dest="loglevel", help="Default: debug.")

    # If called, provide it with the path to the old agent
    parser.add_option("--update", default="", dest="old_agent_path",
                      help=("Should only be used to flag an update. "
                            "Current agent path must be provided."))
    parser.add_option("--agentid", default="", dest="agentid")
    parser.add_option("--operationid", default="", dest="operationid")
    parser.add_option("--appid", default="", dest="appid")

    return parser.parse_args()

if __name__ == '__main__':
    #check_privilege()
    #check_bit_type()
    args = get_input()[0]
    installer = get_installer()

    if args.old_agent_path:
        installer.update(args)
    else:
        installer.install(args)
