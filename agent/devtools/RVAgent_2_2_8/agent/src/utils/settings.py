"""
Helps read agent settings from the agent.config file. As of now, its read-only.
It won't save any changes back to the file.
"""
import ConfigParser
import sys
import os
import shutil

from utils import logger

# Use this value to fill in a key that the server requires
# but the agent wasn't able to find out.
EmptyValue = ''

# Epoch time
DATE_FORMAT = '%s'

AgentName = None
AgentVersion = None
AgentDescription = None
AgentInstallDate = None

_config = None

default_decoder = 'unicode-escape'
default_encoder = 'utf-8'

_app_settings_section = 'appSettings'
_agent_info_section = 'agentInfo'

_app_config_file = 'agent.config'
_server_host_name = None
_db_filename = 'agent.adb'
_server_crt_file = 'server.crt'

starting_directory = os.getcwd()
AgentDirectory = starting_directory  # '/opt/TopPatch/agent'
BinDirectory = os.path.join(AgentDirectory, 'bin')
DbDirectory = os.path.join(AgentDirectory, 'db')
AgentDb = os.path.join(DbDirectory, _db_filename)
EtcDirectory = os.path.join(AgentDirectory, 'etc')
LogDirectory = os.path.join(AgentDirectory, 'logs')
TempDirectory = os.path.join(AgentDirectory, 'tmp')
CertsDirectory = os.path.join(EtcDirectory, 'certs')
PluginDirectory = os.path.join(AgentDirectory, 'plugins')
UpdatesDirectory = os.path.join(TempDirectory, 'updates')

ServerCert = os.path.join(CertsDirectory, _server_crt_file)

operation_queue_file = os.path.join(EtcDirectory, '.oqd')
result_queue_file = os.path.join(EtcDirectory, '.rqd')
reboot_file = os.path.join(EtcDirectory, '.reboot')
shutdown_file = os.path.join(EtcDirectory, '.shutdown')
update_file = os.path.join(EtcDirectory, '.agent_update')

ServerAddress = None
ServerIpAddress = None
ServerHostname = None
ServerPort = None
AgentPort = None
AgentId = None
LogLevel = None
Username = None
Password = None
Customer = None


def _get_server_addresses():

    server_hostname = _config.get(_app_settings_section, 'ServerHostname')
    server_ip_address = _config.get(_app_settings_section, 'ServerIpAddress')

    if server_hostname == '' and server_ip_address == '':

        logger.critical(
            "No valid hostname or ip address was given for the RV Server."
        )
        logger.critical(
            "Please edit agent.config "
            "(in the TopPatch/agent directory) to correct it."
        )

        sys.exit(1)

    else:

        return server_hostname, server_ip_address


def _create_directories():

    if not os.path.exists(DbDirectory):
        os.makedirs(DbDirectory)

    if not os.path.exists(PluginDirectory):
        os.makedirs(PluginDirectory)

    if not os.path.exists(LogDirectory):
        os.makedirs(LogDirectory)

    if not os.path.exists(EtcDirectory):
        os.makedirs(EtcDirectory)

    if not os.path.exists(CertsDirectory):
        os.makedirs(CertsDirectory)

    # Delete the temp directory on startup.
    try:
        shutil.rmtree(TempDirectory)
    except:
        pass

    if not os.path.exists(TempDirectory):
        os.makedirs(TempDirectory)


def initialize(appName=None):
    """ This method must be called to initialize the settings,
     otherwise the properties will be None.

    @return: Nothing
    """
    global AgentName
    global AgentVersion
    global AgentDescription
    global AgentInstallDate

    global _config
    global ServerAddress
    global ServerHostname
    global ServerIpAddress
    global ServerPort
    global AgentPort
    global AgentId
    global LogLevel
    global _logger
    global Username
    global Password
    global Customer

    _create_directories()

    _config = ConfigParser.ConfigParser()
    _config.read(_app_config_file)

    ServerPort = int(_config.get(_app_settings_section, 'serverport'))
    AgentPort = int(_config.get(_app_settings_section, 'agentport'))
    LogLevel = _config.get(_app_settings_section, 'loglevel')
    AgentId = _config.get(_app_settings_section, 'agentid')
    Username = _config.get(_app_settings_section, 'nu')
    Password = _config.get(_app_settings_section, 'wp')
    Customer = _config.get(_app_settings_section, 'customer')

    AgentName = _config.get(_agent_info_section, 'name')
    AgentVersion = _config.get(_agent_info_section, 'version')
    AgentDescription = _config.get(_agent_info_section, 'description')
    AgentInstallDate = _config.get(_agent_info_section, 'installdate')

    if not appName:
        appName = 'agent'

    logger.initialize(appName, LogDirectory, LogLevel)

    ServerHostname, ServerIpAddress = _get_server_addresses()

    if ServerHostname != '':
        ServerAddress = ServerHostname
    else:
        ServerAddress = ServerIpAddress


def save_settings():
    """ Saves the settings to the agent config file.
    @return: Nothing
    """

    # TODO: should be tested before used.

    _config.set(_app_settings_section, 'customer', Customer)
    _config.set(_app_settings_section, 'loglevel', LogLevel)
    _config.set(_app_settings_section, 'agentport', AgentPort)
    _config.set(_app_settings_section, 'serverport', ServerPort)
    _config.set(_app_settings_section, 'serveripaddress', ServerIpAddress)
    _config.set(_app_settings_section, 'serverhostname', ServerHostname)
    _config.set(_app_settings_section, 'agentid', AgentId)
    _config.set(_app_settings_section, 'nu', Username)
    _config.set(_app_settings_section, 'wp', Password)

    _config.set(_agent_info_section, 'name', AgentName)
    _config.set(_agent_info_section, 'version', AgentVersion)
    _config.set(_agent_info_section, 'description', AgentDescription)
    _config.set(_agent_info_section, 'installdate', AgentInstallDate)

    with open(_app_config_file, 'w') as f:
        _config.write(f)
