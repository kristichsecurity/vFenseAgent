import os
import tarfile
import shutil
import zipfile

from utils import logger, utilcmds
from utils.distro.mac import DmgMounter


class Updater():
    """ Initial part of the updating should be done in this class. For example:
        untar the update tar file, and calling the install script.
    """

    def __init__(self, current_agent_path=None):
        self.utilcmds = utilcmds.UtilCmds()
        self.current_agent_path = current_agent_path

        if not self.current_agent_path:
            file_path = os.path.abspath(__file__)

            if '/opt/TopPatch/agent' in file_path:
                self.current_agent_path = '/opt/TopPatch/agent'
            else:
                self.current_agent_path = None
                logger.error("Could not find Application's path.")

        self.update_directory = None

    def _mount_dmg(self, path):
        self.dmg = DmgMounter.DmgMounter()

        return self.dmg.mount_dmg(path)

    def _decompress_tar(self, path):
        tar_name = os.path.basename(path)
        path_dir = os.path.dirname(path)

        tar = tarfile.open(path)
        tar.extractall(path_dir)
        tar.close()

        return os.path.join(path_dir, tar_name.split('.')[0])

    def _decompress_zip(self, path):
        zip_name = os.path.basename(path)
        path_dir = os.path.dirname(path)

        zip = zipfile.ZipFile(path)
        zip.extractall(path_dir)
        zip.close()

        return os.path.join(path_dir, zip_name.split('.')[0])

    def _decompress_update_file(self, update_path):
        """
        Decompresses the file if needed, and returns the path of the
        decompressed file.
        """

        if update_path:
            file_name = os.path.basename(update_path)

            if 'dmg' in file_name.split('.'):
                return self._mount_dmg(update_path)

            elif 'tar' in file_name.split('.'):
                return self._decompress_tar(update_path)

            elif 'zip' in file_name.split('.'):
                return self._decompress_zip(update_path)

        return update_path

    def clean_up(self, update_path):
        # Was properly mounted/decompressed, therefore cleanup required
        if self.update_directory:
            try:
                if self.update_path.endswith('dmg'):
                    if not self.dmg:
                        self.dmg = DmgMounter.DmgMounter()

                    self.dmg.eject_dmg(self.update_directory)
                else:
                    shutil.rmtree(self.update_directory)

            except Exception as e:
                logger.error("Failed to clean up.")
                logger.exception(e)

    def update(self, update_path, extra_cmds=None):
        """ Run this method to begin the update process. """
        logger.debug("Received agent update call.")

        if extra_cmds is None:
            extra_cmds = []

        success = 'false'
        error = ''

        try:
            self.update_directory = \
                self._decompress_update_file(update_path)

            if self.update_directory and self.current_agent_path:
                cmd = ['./install', '--update', self.current_agent_path]
                cmd.extend(extra_cmds)

                # Begin process and don't look back. os.setgrp gives the
                # subprocess a different process group; When daemon is killed
                # it won't affect the process.
                self.utilcmds.run_command_separate_group(
                    cmd, self.update_directory
                )

                logger.debug("Install script called with {0}.".format(cmd))

                # Send back empty string for success so that it is known that
                # the update is in process
                return '', error

            if not os.path.exists(self.update_directory):
                # Space in the end in case of appendage
                error += "Could not decompress. "

            if not self.current_agent_path:
                # Space in the end in case of appendage
                error += "Could not find current agent install path. "

            if error:
                logger.error(error)

        except Exception as e:
            error = "Failed the updating process."
            logger.error(error)
            logger.exception(e)

            self.clean_up(update_path)

        return success, error
