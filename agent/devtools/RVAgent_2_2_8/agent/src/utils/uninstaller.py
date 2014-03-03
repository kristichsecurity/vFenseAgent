
from utils import logger, utilcmds

class Uninstaller():

    def __init__(self):
        self.utilcmds = utilcmds.UtilCmds()

    def uninstall(self):
        try:
            cmd = ['/opt/TopPatch/agent/agent_utils',
                   '--uninstall',
                   '/opt/TopPatch']

            self.utilcmds.run_command_separate_group(cmd)

        except Exception as e:
            logger.error("Failed to uninstall agent.")
            logger.exception(e)
