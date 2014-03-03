from utils import settings

from serveroperation.sofoperation import SofOperation
from serveroperation.sofoperation import OperationKey
from serveroperation.sofoperation import OperationError


class MonitOperationValue():
    # The corresponding SOF equivalent. (Case sensitive)
    MonitorData = 'monitor_data'


class MonitKey(OperationKey):
    # The corresponding SOF equivalent. (Case sensitive)
    Used = 'used'
    Free = 'free'
    PercentUsed = 'used_percent'
    PercentFree = 'free_percent'
    Memory = 'memory'
    Cpu = 'cpu'
    FileSystem = 'file_system'
    User = 'user'
    System = 'system'
    Idle = 'idle'
    Name = 'name'
    Mount = 'mount'


class MonitError(OperationError):
    pass


class MonitUrn():

    # Must not start with a '/'
    MonitorData = 'rvl/v1/{0}/monitoring/monitordata'

    @staticmethod
    def get_monit_data_urn():
        return MonitUrn.MonitorData.format(settings.AgentId)


class MonitOperation(SofOperation):

    def __init__(self, message=None):
        super(MonitOperation, self).__init__(message)

        # TODO: Fix hack. Lazy to use monitplugin module b/c of circular deps.
        self.plugin = 'monitor'
        self.urn_response = ''
        self.request_method = ''

        # TODO: these are no longer used, is that a good idea?
        self.memory = {
            MonitKey.Used: 0, MonitKey.PercentUsed: 0,
            MonitKey.Free: 0, MonitKey.PercentFree: 0
        }

        self.cpu = {
            MonitKey.User: 0,
            MonitKey.System: 0,
            MonitKey.Idle: 0
        }

        self.file_system = []

    def _is_savable(self):
        if not super(MonitOperation, self)._is_savable():
            return False

        non_savable = [MonitOperationValue.MonitorData]

        if self.type in non_savable:
            return False

        return True
