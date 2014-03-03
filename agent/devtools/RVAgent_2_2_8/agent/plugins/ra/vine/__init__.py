import os
import stat
import subprocess

from utils import settings
from utils import systeminfo
from utils import logger

VinePath = os.path.join(settings.BinDirectory, 'vine-server')

_vine_started = False

_process = None

_vine_pwd_file = os.path.join(settings.EtcDirectory, ".vinesettings")
_osx_pwd_file = os.path.join(settings.EtcDirectory, ".osxvncsettings")

_osx_kickstart_path = (
    '/System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/'
    'Resources/kickstart'
)


def _stop_osx_vnc():

    if not os.path.exists(_osx_kickstart_path):
        return False, 'Kickstart script not found.'

    cmd = [
        _osx_kickstart_path,
        '-deactivate',
        '-configure',
        '-access',
        '-off'
    ]

    _process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    output, error = _process.communicate()

    return True


def _start_osx_vnc(pwd):

    global _process

    if not os.path.exists(_osx_kickstart_path):
        return False, 'Kickstart script not found.'

    # Have to stop it first just incase its running with different unexpected
    # settings. ie password, permissions, etc.
    _stop_osx_vnc()

    cmd = [
        _osx_kickstart_path,
        '-activate', '-configure',
        '-access', '-on', '-restart',
        '-agent', '-privs', '-all',
        '-clientopts', '-setvnclegacy',
        '-vnclegacy', 'yes', '-setvncpw',
        '-vncpw', pwd
    ]

    _process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    output, error = _process.communicate()

    return True


def _start_vine_vnc(port):

    global _process

    cmd = [
        VinePath,
        "-rfbport", port,
        "-desktop", systeminfo.computer_name(),
        "-rfbauth", _vine_pwd_file,
        #"-SystemServer", "1",
        "-restartonuserswitch", "N",
        "-UnicodeKeyboard", "0",
        "-keyboardLoading", "N",
        "-pressModsForKeys", "N",
        "-EventTap", "3",
        "-EventSource", "2",
        "-swapButtons",
        "-rendezvous", "Y"
    ]

    _process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return True


def start(port=None):
    """Start the Vine server.

    Args:

        - port: Local port (as a str type) the vine server will listen on.

    Returns:

        - A tuple of two values (bool, str) indicating successful or not. If
        not a string explain the error.

    """

    if not port:
        return(
            False,
            "Valid local port was not provided."
        )

    result = False
    error = ''

    try:

        if not isinstance(port, basestring):
            port = str(port)

        #start_osx_vnc(_osxvnc_read_password())
        _start_vine_vnc(port)

        result = True

    except Exception as e:

        logger.error('Unable to start the vine server.')
        logger.exception(e)

        error = (
            'Agent was unable to start the VNC server. '
            'Exception: %s' % str(e)
        )

    return result, error


def stop():
    """Stops the currently running vine server.

    Returns:

        - Returns True if successful. False otherwise.
    """

    msg = "Vine might not be running."

    if _process:

        try:

            _process.terminate()
            return True, ''

        except Exception as e:

            error = 'Issue trying to stop the vine server.'
            msg = error

            logger.error(error)
            logger.exception(e)

    return False, msg


def _vine_set_password(pwd=None):
    pwd_cmd = os.path.join(settings.BinDirectory, "storepasswd")
    msg = ''

    try:

        if os.path.exists(_vine_pwd_file):
            os.remove(_vine_pwd_file)

        process = subprocess.Popen(
            [pwd_cmd, pwd, _vine_pwd_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        output, error = process.communicate()

        if "storing password succeeded." in output:
            return True, ""

        msg += output
        if error:
            msg += error

    except Exception as e:

        error = "Unable to save vine password."
        msg += error

        logger.error(error)
        logger.exception(e)

    return False, msg


def _osxvnc_set_password(pwd=None):

    msg = ''

    try:

        if os.path.exists(_osx_pwd_file):
            os.remove(_osx_pwd_file)

        with os.fdopen(
            os.open(
                _osx_pwd_file,
                os.O_WRONLY | os.O_CREAT,
                stat.S_IRUSR | stat.S_IWUSR  # "600" permissions
            ),
            'w'
        ) as handle:
            handle.write(pwd + '\n')

    except Exception as e:

        error = "Unable to save vine password."
        msg += error

        logger.error(error)
        logger.exception(e)

    return False, msg


def _osxvnc_read_password():

    if not os.path.exists(_osx_pwd_file):
        save_password('raadmin')

    with open(_osx_pwd_file, 'r') as handle:
        lines = handle.read()
        lines = lines.splitlines()
        if len(lines) >= 1:
            return lines[0]
        else:
            return lines


def save_password(pwd=None):
    """Saves the vine password.

    Args:

        - pwd: Password (str) to save.

    Return:

        - True if save successfully. False otherwise.

    """

    if not pwd:
        return False

    #return _osxvnc_set_password(pwd)
    return _vine_set_password(pwd)

#if not os.path.exists(_osx_pwd_file):
if not os.path.exists(_vine_pwd_file):
    save_password('raadmin')
