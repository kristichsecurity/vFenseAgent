import subprocess

from utils import logger

class DmgMounter:
    def __init__(self):
        self.hdiutil_cmd = '/usr/bin/hdiutil'

    def mount_dmg(self, dmg):
        """Mounts the image give.

        Args:

            - dmg: Image to mount.

        Returns:

            - The mount point if successful. None otherwise.
        """

        cmd = [self.hdiutil_cmd, 'attach', '-nobrowse', dmg]
        mount_point = None

        try:

            process = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE
            )
            raw_output, _stderr = process.communicate(input="Y")

            raw_output = raw_output.replace(
                '\t', '').replace('\n', '').split(' ')

            output = [o for o in raw_output if o != '']

            logger.debug("Mount output: {} ".format(output))

            for i in range(len(output)):

                if output[i] == 'Apple_HFS':

                    mount_point = output[i + 1]

                    # Just in case there is more to the mount point separated
                    # by white spaces.
                    for x in output[i+2:]:
                        mount_point += " {}".format(x)

                    break

        except Exception as e:

            logger.error("Could not mount %s." % dmg)
            logger.exception(e)

        return mount_point

    def eject_dmg(self, mount_point):
        """Ejects the mount point give.

        Args:

            - mount_point: Mount point to eject. (ie: /Volumes/Image.dmg)

        Returns:

            - True if ejected successfully; False otherwise.
        """

        cmd = [self.hdiutil_cmd, 'detach', mount_point]
        ejected = False

        try:

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE
            )

            raw_output, _stderr = process.communicate()

            error_message = ''

            for line in raw_output.splitlines():

                if 'ejected' in line:

                    ejected = True
                    break

                else:

                    error_message += line

        except Exception as e:
            logger.error("Could not eject %s" % mount_point)
            logger.exception(error_message)
            logger.exception(e)

        return ejected
