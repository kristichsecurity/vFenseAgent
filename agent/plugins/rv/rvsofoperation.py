import json

from collections import namedtuple

from serveroperation.sofoperation import SofOperation
from serveroperation.sofoperation import OperationError

from utils import logger
from utils import settings


class RvOperationValue():
    # The corresponding SOF equivalent. (Case sensitive)
    InstallUpdate = 'install_os_apps'
    InstallSupportedApps = 'install_supported_apps'
    InstallCustomApps = 'install_custom_apps'
    InstallAgentUpdate = 'install_agent_update'

    InstallOperations = [InstallUpdate, InstallSupportedApps,
                         InstallCustomApps, InstallAgentUpdate]

    Uninstall = 'uninstall'
    UninstallAgent = 'uninstall_agent'
    UpdatesAvailable = 'updates_available'
    ApplicationsInstalled = 'applications_installed'
    RefreshApps = 'updatesapplications'

    AgentLogRetrieval = 'agent_log_retrieval'

    ThirdPartyInstall = 'third_party_install'

    ExecuteCommand = 'execute_command'

    IgnoredRestart = 'none'
    OptionalRestart = 'needed'
    ForcedRestart = 'force'


class RvUrn():
    """
    This class is directly linked with the install/uninstall operations.
    """

    # URN's Must not start with a '/'

    InstallResult = 'rvl/rv/install/results'

    # Replace the {0} with agent id
    InstallUpdateResult = 'rvl/v1/{0}/rv/results/install/apps/os'
    InstallSupportedApps = 'rvl/v1/{0}/rv/results/install/apps/supported'
    InstallCustomApps = 'rvl/v1/{0}/rv/results/install/apps/custom'
    InstallAgentUpdate = 'rvl/v1/{0}/rv/results/install/apps/agent'

    UninstallResult = 'rvl/v1/{0}/rv/results/uninstall'

    RefreshApps = 'rvl/v1/{0}/rv/updatesapplications'

    # TODO: Implement
    AgentLogRetrieval = 'somedestination'

    @staticmethod
    def get_operation_urn(op_name):
        if RvOperationValue.InstallUpdate == op_name:
            return RvUrn.get_install_update_result_urn()

        if RvOperationValue.InstallSupportedApps == op_name: 
            return RvUrn.get_install_supported_apps_urn()

        if RvOperationValue.InstallCustomApps == op_name:
            return RvUrn.get_install_custom_apps_urn()

        if RvOperationValue.InstallAgentUpdate == op_name: 
            return RvUrn.get_install_agent_update_urn()

        if RvOperationValue.Uninstall == op_name: 
            return RvUrn.get_uninstall_result_urn()

        if RvOperationValue.RefreshApps == op_name: 
            return RvUrn.get_refresh_apps_urn()

    @staticmethod
    def get_install_update_result_urn():
        return RvUrn.InstallUpdateResult.format(settings.AgentId)

    @staticmethod
    def get_install_supported_apps_urn():
        return RvUrn.InstallSupportedApps.format(settings.AgentId)

    @staticmethod
    def get_install_custom_apps_urn():
        return RvUrn.InstallCustomApps.format(settings.AgentId)

    @staticmethod
    def get_install_agent_update_urn():
        return RvUrn.InstallAgentUpdate.format(settings.AgentId)

    @staticmethod
    def get_uninstall_result_urn():
        return RvUrn.UninstallResult.format(settings.AgentId)

    @staticmethod
    def get_refresh_apps_urn():
        return RvUrn.RefreshApps.format(settings.AgentId)

    @staticmethod
    def get_agent_log_retrieval_urn():
        return RvUrn.AgentLogRetrieval


class RvOperationKey():
    # The corresponding SOF equivalent. (Case sensitive)
    Uri = 'uri'
    Uris = 'app_uris'
    Name = 'app_name'
    Hash = 'hash'
    AppId = 'app_id'
    Restart = 'restart'
    PackageType = 'pkg_type'
    CliOptions = 'cli_options'
    CpuThrottle = 'cpu_throttle'
    ThirdParty = 'supported_third_party'

    FileData = 'file_data'
    FileHash = 'file_hash'
    FileName = 'file_name'
    FileUri = 'file_uri'
    FileUris = 'file_uris'
    FileSize = 'file_size'


class RvError(OperationError):

    UpdateNotFound = 'Update not found.'
    UpdatesNotFound = 'No updates found.'
    ApplicationsNotFound = 'No applications found.'


class CpuPriority():

    BelowNormal = 'below_normal'
    Normal = 'normal'
    AboveNormal = 'above_normal'
    Idle = 'idle'
    High = 'high'

    @staticmethod
    def get_niceness(throttle_value):
        niceness_values = {
            CpuPriority.BelowNormal: 5,
            CpuPriority.Normal: 0,
            CpuPriority.Idle: 0,
            CpuPriority.AboveNormal: -5,
            CpuPriority.High: -10
        }

        return niceness_values.get(throttle_value, 0)


class InstallData():

    def __init__(self):

        self.name = ""
        self.id = ""
        # TODO: remove uris when file_data is up and ready
        self.uris = []
        self.file_data = []
        self.third_party = False
        self.cli_options = ""
        self.downloaded = False
        self.proc_niceness = 0

    def __repr__(self):
        return "InstallData(name=%s, id=%s, uris=%s)" % (
            self.name, self.id, self.uris)


class UninstallData():

    def __init__(self):

        self.name = ""
        self.id = ""
        self.third_party = False
        self.cli_options = ""


class RvSofOperation(SofOperation):

    def __init__(self, message=None):
        super(RvSofOperation, self).__init__(message)

        self.applications = []

        # TODO: Fix hack. Lazy to use rvplugin module because of circular deps.
        self.plugin = 'rv'
        self.cpu_priority = self._get_cpu_priority()

        if self.type in RvOperationValue.InstallOperations:

            self.install_data_list = self._load_install_data()
            if RvOperationKey.Restart in self.json_message:

                self.restart = self.json_message[RvOperationKey.Restart]
            else:
                self.restart = RvOperationValue.IgnoredRestart

        elif self.type == RvOperationValue.Uninstall:

            self.uninstall_data_list = self._load_uninstall_data()

        elif self.type == RvOperationValue.ThirdPartyInstall:

            self.cli_options = self.json_message[RvOperationKey.CliOptions]
            self.package_urn = self.json_message[RvOperationKey.Uris]

    def _get_cpu_priority(self):
        return self.json_message.get(
            RvOperationKey.CpuThrottle, CpuPriority.Normal
        )

    def _load_install_data(self):
        """Parses the 'data' key to get the application info for install.

        Returns:

            A list of InstallData types.
        """

        install_data_list = []

        if RvOperationKey.FileData in self.json_message:
            data_list = self.json_message[RvOperationKey.FileData]
        else:
            data_list = []

        try:

            for data in data_list:

                install_data = InstallData()

                install_data.name = data[RvOperationKey.Name]
                install_data.id = data[RvOperationKey.AppId]
                install_data.cli_options = \
                    data.get(RvOperationKey.CliOptions, '')
                install_data.proc_niceness = \
                    CpuPriority.get_niceness(self._get_cpu_priority())

                if RvOperationKey.Uris in data:

                    install_data.uris = data[RvOperationKey.Uris]

                install_data_list.append(install_data)

        except Exception as e:

            logger.error("Could not load install data.")
            logger.exception(e)

        return install_data_list

    def _load_uninstall_data(self):
        """Parses the 'data' key to get the application info for uninstall.

        Returns:

            A list of UninstallData types.

        """

        uninstall_data_list = []

        try:

            if RvOperationKey.FileData in self.json_message:
                data_list = self.json_message[RvOperationKey.FileData]
            else:
                data_list = []

            for data in data_list:

                uninstall_data = UninstallData()

                uninstall_data.name = data[RvOperationKey.Name]
                uninstall_data.id = data[RvOperationKey.AppId]
                #uninstall_data.cli_options = data.get(RvOperationKey.CliOptions, '')

                uninstall_data_list.append(uninstall_data)

        except Exception as e:

            logger.error("Could not load uninstall data.")
            logger.exception(e)

        return uninstall_data_list

    def _is_savable(self):
        if not super(RvSofOperation, self)._is_savable():
            return False

        non_savable = [RvOperationValue.RefreshApps]

        if self.type in non_savable:
            return False

        return True


# Simple nametuple to contain install results.
InstallResult = namedtuple(
    'InstallResult',
    ['successful', 'error', 'restart',
     'app_json', 'apps_to_delete', 'apps_to_add']
)

UninstallResult = namedtuple(
    'UninstallResult', ['success', 'error', 'restart']
)


# TODO: should I be inheriting from RvSofOperation?
class RvSofResult(RvSofOperation):
    """ Data structure for install/uninstall operation results. """

    def __init__(self, operation_id, operation_type, app_id, apps_to_delete,
                 apps_to_add, success, reboot_required, error, data,
                 urn_response, request_method):

        self.id = operation_id  # "uuid"
        self.success = success  # "true" or "false"
        self.reboot_required = reboot_required  # "true" or "false"
        self.error = error  # "error message"
        self.app_id = app_id  # "36 char uuid or 64 char hash"
        self.apps_to_delete = apps_to_delete
        self.apps_to_add = apps_to_add
        self.data = data  # Application instance in json
        self.urn_response = urn_response
        self.request_method = request_method

        self.type = operation_type
        self.raw_result = self.to_json()

    def to_json(self):
        root = {"operation_id": self.id,
                "operation": self.type,
                "success": self.success,
                "reboot_required": self.reboot_required,
                "error": self.error,
                "app_id": self.app_id,
                "apps_to_delete": self.apps_to_delete,
                "apps_to_add": self.apps_to_add,
                "data": self.data}

        return json.dumps(root)

    def update_raw_result(self):
        self.raw_result = self.to_json()
