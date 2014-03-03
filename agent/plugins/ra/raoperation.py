from serveroperation.sofoperation import SofOperation
from serveroperation.sofoperation import OperationKey
from serveroperation.sofoperation import OperationError


class RaValue():
    # The corresponding SOF equivalent. (Case sensitive)
    StartRemoteDesktop = 'start_remote_desktop'
    StopRemoteDesktop = 'stop_remote_desktop'
    RemoteDesktopPassword = 'set_rd_password'


class RaKey(OperationKey):
    # The corresponding SOF equivalent. (Case sensitive)
    TunnelNeeded = 'tunnel_needed'
    HostPort = 'host_port'
    SSHPort = 'ssh_port'
    Error = 'error'
    Success = 'success'
    Password = 'password'


class RaError(OperationError):
    pass


class RaUrn():

    # must not start with a '/'
    RdResults = 'rvl/ra/rd/results'
    PasswordSet = 'rvl/ra/rd/password'


class RaOperation(SofOperation):

    def __init__(self, message=None):
        super(RaOperation, self).__init__(message)

        # TODO: Fix hack. Lazy to use raplugin module b/c of circular deps.
        self.plugin = 'ra'
        self.error = ''
        self.success = None

        if OperationKey.Data in self.json_message:

            data = self.json_message[OperationKey.Data]

            if RaKey.TunnelNeeded in data:
                self.tunnel_needed = data[RaKey.TunnelNeeded]
            else:
                self.tunnel_needed = False

            if RaKey.HostPort in data:
                self.host_port = data[RaKey.HostPort]
            else:
                self.host_port = None

            if RaKey.SSHPort in data:
                self.ssh_port = data[RaKey.SSHPort]
            else:
                self.ssh_port = None

            if RaKey.Password in data:
                self.password = data[RaKey.Password]
            else:
                self.password = ""
