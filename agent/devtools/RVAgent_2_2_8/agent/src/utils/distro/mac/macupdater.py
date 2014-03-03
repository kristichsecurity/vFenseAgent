import os
import subprocess

from utils import logger
import DmgMounter

class MacUpdater():
    """Initial part of the updating should be done here. For example:
       downloading the update/dmg, mounting the image, and running the
       update module from the image in a separate process.
    """
    def __init__(self, current_app_path=None):
        self.dmg = DmgMounter.DmgMounter()

        self.current_app_path = current_app_path

        if not self.current_app_path:
            file_path = os.path.abspath(__file__)

            if '/opt/TopPatch/agent' in file_path:
                self.current_app_path = '/opt/TopPatch/agent'
            else:
                self.current_app_path = None
                logger.error("Could not find Application's path.")

    def update(self, path_of_update, extra_cmds=[]):
        """Run this method to begin the update process."""
        logger.debug("macupdater.py: received update call.")

        success = 'false'
        error = ''

        try:
            mount_point = self.dmg.mount_dmg(path_of_update)
            logger.debug("macupdater.py: mount point = " + mount_point)

            if os.path.exists(mount_point) and self.current_app_path:
                #install_script = os.path.join(mount_point, 'install')
                #logger.debug(
                #    "macupdater.py: install script path = " + install_script
                #)

                #cmd = [install_script, '--update', self.current_app_path]
                cmd = ['./install', '--update', self.current_app_path]
                cmd.extend(extra_cmds)

                logger.debug(
                    "macupdater.py: This is the cmd for installer: " + str(cmd)
                )

                # Begin process and don't look back. os.setgrp gives the
                # subprocess a different process group; When daemon is killed
                # it won't affect the process.
                subprocess.Popen(cmd, preexec_fn=os.setpgrp, cwd=mount_point)

                logger.debug("macupdater.py: install script called.") 

                # Send back empty string for success so that it is known that
                # the update is in process
                return '', error

            if not os.path.exists(mount_point):
                error = "Could not mount agent dmg."
                logger.error(error)

            if not self.current_app_path:
                error = "Could not find current agent install path."
                logger.error(error)

        except Exception as e:
            error = "Failed the updating process."
            logger.error(error)
            logger.exception(e)

            try:
                if mount_point:
                    self.dmg.eject_dmg(mount_point)
            except Exception as e2:
                logger.error("Failed to unmount the update image.")
                logger.exception(e2)

        return success, error

