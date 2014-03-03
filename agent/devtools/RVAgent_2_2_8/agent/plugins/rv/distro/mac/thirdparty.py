"""
Module to manage everything and anything with RV supported third party
applications. Fun!
"""
import os
import subprocess

from utils import logger
from rv.data.application import Application
from rv.data.application import CreateApplication


class ThirdPartyManager():

    @staticmethod
    def get_supported_installs():

        apps = []

        java = ThirdPartyManager.oracle_jre_install()
        if java:

            apps.append(java)

        return apps

    @staticmethod
    def oracle_jre_install():

        JRE7_root_path = '/Library/Internet Plug-Ins/JavaAppletPlugin.plugin/'
        JRE7_command = os.path.join(JRE7_root_path, 'Contents/Home/bin/java')

        application = CreateApplication.null_application()

        try:

            if os.path.exists(JRE7_command):

                # For some sane reason, '-version' spits output to the
                # stderr...
                output = subprocess.check_output([JRE7_command, '-version'],
                                                 stderr=subprocess.STDOUT)

            # Output example:
            # java version "1.7.0_21"
            # Java(TM) SE Runtime Environment (build 1.7.0_21-b12)
            # Java HotSpot(TM) 64-Bit Server VM (build 23.21-b01, mixed mode)

                if '64-Bit' in output.splitlines()[2]:

                    bit_type = '64'

                else:

                    bit_type = '32'

                app_name = 'Java ' + bit_type
                app_vendor_name = 'Oracle'

                raw_ver = 'NA'

                try:

                    raw_ver = output.splitlines()[0].split('"')[1]
                    version = raw_ver.replace('_', '.') + '0'
                    app_version = version.partition('.')[2]

                except Exception as e:

                    logger.error("Unknown Java version format: %s" % raw_ver)
                    app_version = ''

                try:

                    s = os.stat(JRE7_command)
                    #app.install_date = datetime.fromtimestamp(
                    #    s.st_ctime).strftime('%m/%d/%Y')
                    app_install_date = s.st_ctime

                except Exception as e:

                    logger.error("Could not verify install date.")
                    logger.exception(e)

                    app_install_date = None

                application = CreateApplication.create(
                    app_name,
                    app_version,
                    '',  # description
                    [],  # file_data
                    [],  # dependencies
                    '',  # support_url
                    '',  # vendor_severity
                    '',  # file_size
                    '',  # vendor_id,
                    app_vendor_name,  # vendor_name
                    app_install_date,  # install_date
                    None,  # release_date
                    True,  # installed
                    "",  # repo
                    "no",  # reboot_required
                    "yes"  # TODO: check if app is uninstallable
                )

        except Exception as e:

            logger.error("Could not verify Oracle Java install.")
            logger.exception(e)

        return application
