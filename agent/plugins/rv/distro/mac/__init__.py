import os
import subprocess
import glob
import shutil
import errno
import time

from utils import settings
from utils import logger
from utils.distro.mac import launchd
from utils.distro.mac.plist import PlistInterface

from rv.rvsofoperation import CpuPriority


class PkgInstaller():
    """ A class to install Mac OS X packages using '/usr/sbin/installer'.
    Helps with making the calls and parsing the output to get the results.
    """

    def __init__(self):

        self.ptyexec_cmd = os.path.join(settings.BinDirectory, 'ptyexec')
        self.installer_cmd = '/usr/sbin/installer'
        self.softwareupdate_cmd = '/usr/sbin/softwareupdate'

        self.plist = PlistInterface()

    # Uses installer tool to install pkgs
    def installer(self, pkg):

        installer_cmd = [self.installer_cmd,
                         '-pkg', '%s' % pkg,
                         '-target', '/']

        process = subprocess.Popen(
            installer_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        raw_output, _stderr = process.communicate()

        unknown_output = []
        success = 'false'
        error = ''

        for output in raw_output.splitlines():

            logger.debug(output)

            # All known output begins with 'installer' so remove it if present.
            if output.find('installer:') == 0:
                output = output.partition(':')[2].strip()

            # Known successful output:
            # 'The upgrade was successful.'
            # 'The install was successful.'
            if 'successful' in output:
                success = 'true'
                error = ''
                break

            elif 'Package name is' in output:
                continue

            # Similar output:
            # Installing at base path
            # Upgrading at base path
            elif 'at base path' in output:
                continue

            else:
                # Assuming failure.
                unknown_output.append(output)
                error = ''

        if len(unknown_output) != 0:
            error = ". ".join([output for output in unknown_output])

        return success, error

    # Old code on how to use softwareupdate to install updates.
    def softwareupdate(self, update_name, proc_niceness):

        #  Need to wrap call to /usr/sbin/softwareupdate with a utility
        # that makes softwareupdate think it is connected to a tty-like
        # device so its output is unbuffered so we can get progress info
        # '-v' (verbose) option is available on OSX > 10.5
        cmd = [
            self.ptyexec_cmd,
            self.softwareupdate_cmd,
            '-v', '-i',
            update_name
        ]
        logger.debug("Running softwareupdate: " + str(cmd))

        success = 'false'
        error = ''

        if not os.path.exists(self.ptyexec_cmd):
            raise PtyExecMissingException(settings.BinPath)

        try:
            job = launchd.Job(cmd, proc_niceness=proc_niceness)
            job.start()
        except launchd.LaunchdJobException as e:
            error_message = 'Error with launchd job (%s): %s' % (cmd, str(e))
            logger.error(error_message)
            logger.critical('Skipping softwareupdate run.')

            return 'false', error_message

        while True:

            output = job.stdout.readline()

            if not output:
                if job.returncode() is not None:
                    break
                else:
                    # no data, but we're still running
                    # sleep a bit before checking for more output
                    time.sleep(2)
                    continue

            # Checking output to verify results.
            output = output.decode('UTF-8').strip()
            if output.startswith('Installed '):
            # 10.6 / 10.7 / 10.8 Successful install of package name.
                success = 'true'
                error = ''
                break

            elif output.startswith('Done with'):
                success = 'true'
                error = ''
                break

            #            elif output.startswith('Done '):
            #                # 10.5. Successful install of package name.
            #                install_successful = True

            elif 'No such update' in output:
                # 10.8 When a package cannot be found.
                success = 'false'
                error = "Update not found."
                break

            elif output.startswith('Error '):
                # 10.8 Error statement
                # Note: Checking for updates doesn't display the
                # 'Error' string when connection is down.
                if "Internet connection appears to be offline" in output:
                    error = "Could not download files."
                else:
                    error = output

                    success = 'false'

                break

            elif 'restart immediately' in output:
                # Ignore if output is indicating a restart. Exact line:
                # "You have installed one or more updates that requires that
                # you restart your computer.  Please restart immediately."
                continue

            elif output.startswith('Package failed'):
                success = 'false'
                error = output
                logger.debug(error)
                break

            elif (
                output == ''
                or output.startswith('Progress')
                or output.startswith('Done')
                or output.startswith('Running package')
                or output.startswith('Copyright')
                or output.startswith('Software Update Tool')
                or output.startswith('Downloading')
                or output.startswith('Moving items into place')
                or output.startswith('Writing package receipts')
                or output.startswith('Removing old files')
                or output.startswith('Registering updated components')
                or output.startswith('Waiting for other installations')
                or output.startswith('Writing files')
                or output.startswith('Cleaning up')
                or output.startswith('Registering updated applications')
                or output.startswith('About')
                or output.startswith('Less than a minute')
            ):
                # Output to ignore
                continue

            elif (
                output.startswith('Checking packages')
                or output.startswith('Installing')
                or output.startswith(
                    'Optimizing system for installed software'
                )
                or output.startswith('Waiting to install')
                or output.startswith('Validating packages')
                or output.startswith('Finding available software')
                or output.startswith('Downloaded')
            ):
                # Output to display
                logger.debug('softwareupdate: ' + output)

            else:
                success = 'false'
                error = "softwareupdate (unknown): " + output
                logger.debug(error)

#        return_code = job.returncode()
#        if return_code == 0:
#            # get SoftwareUpdate's LastResultCode
#            su_path = '/Library/Preferences/com.apple.SoftwareUpdate.plist'
#            su_prefs = plist.convert_and_read_plist(su_path)
#            last_result_code = su_prefs['LastResultCode'] or 0
#            if last_result_code > 2:
#                return_code = last_result_code

        logger.debug("Done with softwareupdate.")
        return success, error

    def _make_dir(self, dir_path):
        try:
            os.makedirs(dir_path)
        except OSError as ose:
            # Avoid throwing an error if path already exists
            if ose.errno != errno.EEXIST:
                logger.error("Failed to create directory: " + dir_path)
                logger.exception(ose)
                raise

    def _move_pkgs(self, install_data, app_plist_data):
        """ Move all pkgs in src to dest. """

        try:
            product_key = app_plist_data["productKey"]

            src = os.path.join(settings.UpdatesDirectory, install_data.id)
            dest = os.path.join('/Library/Updates', product_key)

            if not os.path.exists(dest):
                self._make_dir(dest)
                time.sleep(3)

            for _file in os.listdir(src):
                if _file.endswith(".pkg"):

                    su_pkg_path = os.path.join(dest, _file)
                    if os.path.exists(su_pkg_path):
                        os.remove(su_pkg_path)
                        logger.debug(
                            "Removed existing pkg from /Library/Updates: %s "
                            % su_pkg_path
                        )

                    src_pkg = os.path.join(src, _file)
                    shutil.move(src_pkg, dest)
                    logger.debug("Moved " + _file + " to: " + dest)

        except Exception as e:
            logger.error("Failed moving pkgs to /Library/Updates.")
            logger.exception(e)
            raise

    def _get_app_plist_data(self, install_data):
        app_plist_data = self.plist.get_app_dict_from_plist(
            os.path.join(settings.TempDirectory, "updates.plist"),
            install_data.name
        )

        return app_plist_data

    def _get_softwareupdate_name(self, app_plist_data):
        """
        Construct the name softwareupdate expects for installation out of the
        plist ignore key and the version with a dash in between.
        """
        try:
            ignore_key = app_plist_data["ignoreKey"]
            version = app_plist_data["version"]

            return "-".join([ignore_key, version])

        except Exception as e:
            logger.error("Failed constructing softwareupdate name argument.")
            logger.exception(e)
            raise Exception(e)

    def install(self, install_data):
        success = 'false'
        error = "Failed to install: " + install_data.name

        try:
            app_plist_data = self._get_app_plist_data(install_data)

            self._move_pkgs(install_data, app_plist_data)

            update_name = self._get_softwareupdate_name(app_plist_data)
            success, error = self.softwareupdate(
                update_name, install_data.proc_niceness
            )

        except Exception as e:
            logger.error("Failed to install pkg: " + install_data.name)
            logger.exception(e)

        return success, error

    def _remove_productkey_dir(self, app_plist_data):
        try:
            product_key = app_plist_data["productKey"]
            product_key_dir = os.path.join("/Library/Updates/", product_key)

            if os.path.exists(product_key_dir):
                logger.debug(
                    "%s exists. Attempting to remove it."
                    % product_key_dir
                )
                shutil.rmtree(product_key_dir)
                logger.debug("Removed: " + product_key_dir)

            return True

        except Exception as e:
            logger.error("Failed to remove directory")
            logger.exception(e)
            raise Exception(e)

        return False

    def complete_softwareupdate(self, install_data):
        """
        Removes the product key directory if it exists, and lets
        softwareupdate download and install on its own.
        """

        success = 'false'
        error = "Failed to install: " + install_data.name

        try:
            app_plist_data = self._get_app_plist_data(install_data)

            for i in range(1, 3):
                remove_success = self._remove_productkey_dir(app_plist_data)

                if remove_success:
                    break

                time.sleep(5 * i)

            update_name = self._get_softwareupdate_name(app_plist_data)
            success, error = self.softwareupdate(
                update_name, install_data.proc_niceness
            )

        except Exception as e:
            logger.error(
                "Failed to download/install pkg with softwareupdate: %s"
                % install_data.name
            )
            logger.exception(e)

        return success, error


class DmgInstaller():

    def __init__(self):

        self.hdiutil_cmd = '/usr/bin/hdiutil'

    def install(self, dmg):
        success = 'false'
        error = 'Failed to install from: ' + dmg

        dmg_mount = None

        try:
            dmg_mount = self._mount_dmg(dmg)

            if not dmg_mount:
                return success, 'Failed to mount dmg.'

            app_bundles = glob.glob(os.path.join(dmg_mount, '*.app'))
            pkgs = glob.glob(os.path.join(dmg_mount, '*.pkg'))

            if app_bundles:

                for app in app_bundles:

                    success, error = self.app_bundle_install(app)

                    if success != 'true':

                        break

            elif pkgs:

                pi = PkgInstaller()

                for pkg in pkgs:

                    success, error = pi.installer(pkg)

                    if success != 'true':

                        break

        except Exception as e:
            logger.error("Failed to install: " + str(dmg))
            logger.exception(e)
        finally:
            if dmg_mount:
                self.eject_dmg(dmg_mount)

        return success, error

    def app_bundle_install(self, app_path):
        """ Copies an app bundle (directory that ends in .app) to the
        /Applications directory.

        Args:

            - app_path: Path to the app bundle.

        Returns:

            - True if copied successfully. False otherwise.
        """

        success = 'false'
        error = ''

        app_name = app_path.split('/')[-1]
        install_path = os.path.join('/Applications', app_name)

        try:

            shutil.copytree(app_path, install_path)

            if os.path.exists(install_path):

                success = 'true'

            else:

                error = "Application {} was not installed correctly.".format(
                    app_name
                )

        except Exception as e:

            logger.error("Failed to install {0}.".format(app_path))
            logger.exception(e)
            error = str(e)

            # Remove anything that was moved over.
            if os.path.exists(install_path):
                shutil.rmtree(install_path)

        return success, error

    def mount_dmg(self, dmg, mount_to):

        cmd = [self.hdiutil_cmd,
               'attach',
               '-nobrowse',
               '-mountpoint',
               mount_to,
               dmg]

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        raw_output, _stderr = process.communicate(input="Y")

        if os.path.exists(mount_to):
            return True

        return False

    def _mount_dmg(self, dmg):
        """Mounts the image give.

        Args:

            - dmg: Image to mount.

        Returns:

            - The mount point if successful. None otherwise.
        """

        cmd = [self.hdiutil_cmd, 'attach', '-nobrowse', dmg]
        mount_point = None

        try:

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
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

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
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

            logger.error('Could not eject dmg: %s' % mount_point)
            logger.exception(e)

        return ejected


class Uninstaller():
    """
    Class to uninstall applications. As of this writing, it will only
    uninstall applications in the /Applications directory.

    It also tries its best to remove preferences and caches for said app.
    Searches:
        - /Library/Preferences
        - /Library/Caches
    """

    def __init__(self):
        self.rm_cmd = '/bin/rm'
        self.apps_dir = '/Applications'
        self.lib_prefs_dir = '/Library/Preferences'
        self.lib_caches_dir = '/Library/Caches'

    def remove(self, app_name):
        success = 'false'
        name = '%s.app' % app_name
        app_dir = os.path.join(self.apps_dir, name)
#        rm_cmd = [self.rm_cmd, '-r', '-f']

        # Get the Bundle ID before deleting it.
        # This will delete prefs and caches using the bundle id.
#        plist_file = os.path.join(app_dir, 'Contents/Info.plist')
#        if os.path.exists(plist_file):
#            app_info = self.plist.convert_and_read_plist(plist_file)
#            if 'CFBundleIdentifier' in app_info:
#                bundle_id = app_info['CFBundleIdentifier']
#
#                path_name = os.path.join(self.lib_prefs_dir, bundle_id + '.*')
#                for file in glob.glob(path_name):
#                    cmd_ = list(cmd)
#                    cmd_.append(file)
#                    subprocess.call(cmd)

        try:

            if os.path.exists(app_dir):

                shutil.rmtree(app_dir)
                success = 'true'
                error = ''

            else:

                success = 'false'
                error = 'Application %s not found.' % app_name

        except Exception as e:

            logger.error("Could not uninstall %s." % app_name)
            logger.exception(e)

            error = str(e)

        return success, error


class PtyExecMissingException(Exception):
    """
    Exception if 'ptyexec' is missing.
    """
    def __init__(self, bin_path):
        self.message = "Could not find required 'ptyexec' command."
        self.location = bin_path

    def __repr__(self):
        return self.message + " Path checked: %s" % self.location
