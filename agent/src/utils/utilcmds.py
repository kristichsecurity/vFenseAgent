import os
import subprocess

from utils import settings

class UtilCmds():

    def __init__(self):
        pass

    def run_command(self, cmd):
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        result, err = proc.communicate()

        try:

            result = (
                result.decode(settings.default_decoder)
                      .encode(settings.default_encoder)
            )

        except UnicodeDecodeError:
            result = result.replace('\\', '\\\\')

            # If this fails let the calling function deal with the exception
            result = (
                result.decode(settings.default_decoder)
                      .encode(settings.default_encoder)
            )

        return result, err

    def run_command_separate_group(self, cmd, cwd=None):
        subprocess.Popen(cmd, preexec_fn=os.setpgrp, cwd=cwd)
