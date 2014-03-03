import os
import re
import glob
import time
import subprocess
import hashlib
import urllib

from utils import logger, settings, utilcmds
from utils.distro.mac import macupdater
from utils.distro.mac.plist import PlistInterface
from utils.misc.htmlstripper import BodyHTMLStripper

from rv.rvsofoperation import RvError, InstallResult, UninstallResult
from rv.data.application import CreateApplication
#from rv.distro.mac.macsqlite import SqliteMac, UpdateDataColumn
from rv.distro.mac.thirdparty import ThirdPartyManager
from rv.distro.mac import PkgInstaller, DmgInstaller, Uninstaller
from rv.distro.mac.updatescatalog import UpdatesCatalog


class MacOpHandler():

    def __init__(self):
        # Initialize mac table stuff.
        #self._macsqlite = SqliteMac()
        #self._macsqlite.recreate_update_data_table()
        self.utilcmds = utilcmds.UtilCmds()

        self._catalog_directory = \
            os.path.join(settings.AgentDirectory, 'catalogs')

        self._updates_plist = \
            os.path.join(settings.TempDirectory, 'updates.plist')

        if not os.path.isdir(self._catalog_directory):
            os.mkdir(self._catalog_directory)

        self.pkg_installer = PkgInstaller()
        self.dmg_installer = DmgInstaller()
        self.plist = PlistInterface()
        self.updates_catalog = UpdatesCatalog(
            self._catalog_directory,
            os.path.join(settings.TempDirectory, 'updates_catalog.json')
        )

    def get_installed_applications(self):
        """Parses the output from
        the 'system_profiler -xml SPApplicationsDataType' command.
        """

        logger.info("Getting installed applications.")

        installed_apps = []

        try:

            cmd = ['/usr/sbin/system_profiler',
                   '-xml',
                   'SPApplicationsDataType']

            output, _error = self.utilcmds.run_command(cmd)

            app_data = self.plist.read_plist_string(output)

            for apps in app_data:

                for app in apps['_items']:

                    app_inst = None

                    try:

                        # Skip app, no name.
                        if not '_name' in app:
                            continue

                        app_name = app['_name']
                        app_version = app.get('version', '')
                        app_date = app.get('lastModified', '')

                        app_inst = CreateApplication.create(
                            app_name,
                            app_version,
                            '',  # description
                            [],  # file_data
                            [],  # dependencies
                            '',  # support_url
                            '',  # vendor_severity
                            '',  # file_size
                            '',  # vendor_id,
                            '',  # vendor_name
                            app_date,  # install_date
                            None,  # release_date
                            True,  # installed
                            "",  # repo
                            "no",  # reboot_required
                            "yes"  # TODO: check if app is uninstallable
                        )

                    except Exception as e:
                        logger.error("Error verifying installed application."
                                     "Skipping.")
                        logger.exception(e)

                    if app_inst:
                        installed_apps.append(app_inst)

            installed_apps.extend(
                ThirdPartyManager.get_supported_installs()
            )

        except Exception as e:
            logger.error("Error verifying installed applications.")
            logger.exception(e)

        logger.info('Done.')

        return installed_apps

    def _get_installed_app(self, name, installed_apps):
        for app in installed_apps:
            if app.name == name:
                return app

        return CreateApplication.null_application()

    def _get_installed_apps(self, name_list):
        installed_apps = self.get_installed_applications()

        app_list = []
        found = 0
        total = len(name_list)

        for app in installed_apps:
            if found >= total:
                break

            if app.name in name_list:
                app_list.append(app)
                found += 1

        return app_list

    def get_installed_updates(self):
        """
        Parses the /Library/Receipts/InstallHistory.plist file looking for
        'Software Update' as the process name.
        """

        logger.info("Getting installed updates.")

        install_history = '/Library/Receipts/InstallHistory.plist'
        installed_updates = []

        try:

            if os.path.exists(install_history):

                app_data = self.plist.read_plist(install_history)

                for app in app_data:

                    app_inst = None

                    try:

                        if app.get('processName') == 'Software Update':

                            if not 'displayName' in app:
                                continue

                            app_name = app['displayName']

                            app_name = app.get('displayName', '')
                            app_version = app.get('displayVersion', '')
                            app_date = app.get('date', '')

                            app_inst = CreateApplication.create(
                                app_name,
                                app_version,
                                '',  # description
                                [],  # file_data
                                [],  # dependencies
                                '',  # support_url
                                '',  # vendor_severity
                                '',  # file_size
                                # vendor_id
                                hashlib.sha256(
                                    app_name.encode('utf-8') + app_version)
                                .hexdigest(),
                                'Apple',  # vendor_name
                                app_date,  # install_date
                                None,  # release_date
                                True,  # installed
                                "",  # repo
                                "no",  # reboot_required
                                "yes"  # TODO: check if app is uninstallable
                            )

                    except Exception as e:

                        logger.error("Error verifying installed update."
                                     "Skipping.")
                        logger.exception(e)

                    if app_inst:
                        installed_updates.append(app_inst)

        except Exception as e:
            logger.error("Error verifying installed updates.")
            logger.exception(e)

        logger.info('Done.')

        return installed_updates

    @staticmethod
    def _strip_body_tags(html):
        s = BodyHTMLStripper()
        s.feed(html)
        return s.get_data()

    def _get_softwareupdate_data(self):
        cmd = ['/usr/sbin/softwareupdate', '-l', '-f', self._updates_plist]

        # Little trick to hide the command's output from terminal.
        with open(os.devnull, 'w') as dev_null:
            subprocess.call(cmd, stdout=dev_null, stderr=dev_null)

        cmd = ['/bin/cat', self._updates_plist]
        output, _ = self.utilcmds.run_command(cmd)

        return output

    def create_apps_from_plist_dicts(self, app_dicts):
        applications = []

        for app_dict in app_dicts:
            try:
                # Skip app, no name.
                if not 'name' in app_dict:
                    continue

                app_name = app_dict['name']

                release_date = self._get_package_release_date(app_name)
                file_data = self._get_file_data(app_name)

                dependencies = []

                app_inst = CreateApplication.create(
                    app_name,
                    app_dict['version'],

                    # Just in case there's HTML, strip it out
                    MacOpHandler._strip_body_tags(app_dict['description'])
                    # and get rid of newlines.
                    .replace('\n', ''),

                    file_data,  # file_data
                    dependencies,
                    '',  # support_url
                    '',  # vendor_severity
                    '',  # file_size
                    app_dict['productKey'],  # vendor_id
                    'Apple',  # vendor_name
                    None,  # install_date
                    release_date,  # release_date
                    False,  # installed
                    '',  # repo
                    app_dict['restartRequired'].lower(),  # reboot_required
                    'yes'  # TODO: check if app is uninstallable
                )

                applications.append(app_inst)
                #self._add_update_data(
                #    app_inst.name,
                #    app_dict['restartRequired']
                #)

            except Exception as e:
                logger.error(
                    "Failed to create an app instance for: {0}"
                    .format(app_dict['name'])
                )
                logger.exception(e)

        return applications

    def get_available_updates(self):
        """
        Uses the softwareupdate OS X app to see what updates are available.
        @return: Nothing
        """

        logger.info("Getting available updates.")

        try:

            logger.debug("Downloading catalogs.")
            self._download_catalogs()
            logger.debug("Done downloading catalogs.")

            logger.debug("Getting softwareupdate data.")
            avail_data = self._get_softwareupdate_data()
            logger.debug("Done getting softwareupdate data.")

            logger.debug("Crunching available updates data.")
            plist_app_dicts = \
                self.plist.get_plist_app_dicts_from_string(avail_data)

            self.updates_catalog.create_updates_catalog(plist_app_dicts)

            available_updates = \
                self.create_apps_from_plist_dicts(plist_app_dicts)

            logger.info('Done getting available updates.')

            return available_updates

        except Exception as e:
            logger.error("Could not get available updates.")
            logger.exception(e)

            return []

    def _get_list_difference(self, list_a, list_b):
        """
        Returns the difference of of list_a and list_b.
        (aka) What's in list_a that isn't in list_b
        """
        set_a = set(list_a)
        set_b = set(list_b)

        return set_a.difference(set_b)

    def _get_apps_to_delete(self, old_install_list, new_install_list):

        difference = self._get_list_difference(
            old_install_list, new_install_list
        )

        apps_to_delete = []
        for app in difference:
            root = {}
            root['name'] = app.name
            root['version'] = app.version

            apps_to_delete.append(root)

        return apps_to_delete

    def _get_apps_to_add(self, old_install_list, new_install_list):

        difference = self._get_list_difference(
            new_install_list, old_install_list
        )

        apps_to_add = []
        for app in difference:
            apps_to_add.append(app.to_dict())

        return apps_to_add

    def _get_apps_to_add_and_delete(self, old_install_list,
                                    new_install_list=None):

        if not new_install_list:
            new_install_list = self.get_installed_applications()

        apps_to_delete = self._get_apps_to_delete(
            old_install_list, new_install_list
        )

        apps_to_add = self._get_apps_to_add(
            old_install_list, new_install_list
        )

        return apps_to_add, apps_to_delete

    def _get_app_encoding(self, name, install_list):
        updated_app = self._get_installed_app(name, install_list)
        app_encoding = updated_app.to_dict()

        return app_encoding

    def install_update(self, install_data, update_dir=None):
        """
        Install OS X updates.

        Returns:

            Installation result

        """

        # Use to get the apps to be removed on the server side
        old_install_list = self.get_installed_applications()

        success = 'false'
        error = RvError.UpdatesNotFound
        restart = 'false'
        app_encoding = CreateApplication.null_application().to_dict()
        apps_to_delete = []
        apps_to_add = []

        if not update_dir:
            update_dir = settings.UpdatesDirectory

        #update_data = self._macsqlite.get_update_data(
        #    install_data.name
        #)

        if install_data.downloaded:
            success, error = self.pkg_installer.install(install_data)

            if success != 'true':
                logger.debug(
                    "Failed to install update {0}. success:{1}, error:{2}"
                    .format(install_data.name, success, error)
                )
                # Let the OS take care of downloading and installing.
                success, error = \
                    self.pkg_installer.complete_softwareupdate(install_data)

        else:
            logger.debug(("Downloaded = False for: {0} calling "
                         "complete_softwareupdate.")
                         .format(install_data.name))

            success, error = \
                self.pkg_installer.complete_softwareupdate(install_data)

        if success == 'true':
            #restart = update_data.get(UpdateDataColumn.NeedsRestart, 'false')
            restart = self._get_reboot_required(install_data.name)

            new_install_list = self.get_installed_applications()

            app_encoding = self._get_app_encoding(
                install_data.name, new_install_list
            )

            apps_to_add, apps_to_delete = self._get_apps_to_add_and_delete(
                old_install_list, new_install_list
            )

        return InstallResult(
            success,
            error,
            restart,
            app_encoding,
            apps_to_delete,
            apps_to_add
        )

    def _install_third_party_pkg(self, pkgs):
        success = 'false'
        error = 'Could not install pkgs.'

        if pkgs:
            # TODO(urgent): what to do with multiple pkgs?
            for pkg in pkgs:
                success, error = self.pkg_installer.installer(pkg)

        return success, error

    def _get_app_names_from_paths(self, app_bundle_paths):
        app_bundles = [app.split('/')[-1] for app in app_bundle_paths]

        app_names = [app_bundle.split('.app')[0] for app_bundle in app_bundles]

        return app_names

    def _install_third_party_dmgs(self, dmgs):
        success = 'false'
        error = 'Could not install from dmg.'
        app_names = []

        for dmg in dmgs:
            try:
                dmg_mount = os.path.join('/Volumes', dmg.split('/')[-1])

                if not self.dmg_installer.mount_dmg(dmg, dmg_mount):
                    raise Exception(
                        "Failed to get mount point for: {0}".format(dmg)
                    )

                logger.debug("Custom App Mount ****** : {0}".format(dmg_mount))

                pkgs = glob.glob(os.path.join(dmg_mount, '*.pkg'))
                dmg_app_bundles = glob.glob(os.path.join(dmg_mount, '*.app'))

                if pkgs:
                    success, error = self._install_third_party_pkg(pkgs)

                elif dmg_app_bundles:
                    app_names.extend(
                        self._get_app_names_from_paths(dmg_app_bundles)
                    )

                    for app in dmg_app_bundles:
                        success, error = \
                            self.dmg_installer.app_bundle_install(app)

            except Exception as e:
                logger.error("Failed installing dmg: {0}".format(dmg))
                logger.exception(e)

                success = 'false'

                # TODO: if one dmg fails on an update, should the rest also be
                # stopped from installing?

                break

            finally:
                if dmg_mount:
                    self.dmg_installer.eject_dmg(dmg_mount)

        return success, error, app_names

    def _separate_important_info(self, info):
        """
        Parses info which looks like:
        """

        info = info.split('\n')
        info = [x.split('=') for x in info]

        # Cleaning up both the key and the value
        info = {ele[0].strip(): ele[1].strip() for ele in info
                if len(ele) == 2}

        no_quotes = r'"(.*)"'

        info_dict = {}

        try:
            app_name = info['kMDItemDisplayName']
            app_version = info['kMDItemVersion']
            app_size = info['kMDItemFSSize']
        except KeyError as ke:
            return {}

        no_quote_name = re.search(no_quotes, app_name)
        if no_quote_name:
            app_name = no_quote_name.group(1)

        no_quote_version = re.search(no_quotes, app_version)
        if no_quote_version:
            app_version = no_quote_version.group(1)

        no_quote_size = re.search(no_quotes, app_size)
        if no_quote_size:
            app_size = no_quote_size.group(1)

        info_dict['name'] = app_name
        info_dict['version'] = app_version
        info_dict['size'] = app_size

        return info_dict

    def _get_app_bundle_info(self, app_bundle_path):
        try:
            info_dict = {}

            info_plist_path = \
                os.path.join(app_bundle_path, 'Contents', 'Info.plist')

            plist_dict = self.plist.read_plist(info_plist_path)

            info_dict['name'] = plist_dict['CFBundleName']
            info_dict['version'] = plist_dict['CFBundleShortVersionString']

            #cmd = ['du', '-s', app_bundle_path]
            #output, err = self.utilcmds.run_command(cmd)

            #try:
            #    size = output.split('\t')[0]
            #except Exception as e:
            #    size = 0

            #info_dict['size'] = size

            return info_dict
        except Exception:
            return {}

    def _create_app_from_bundle_info(self, app_bundle_names):
        app_instances = []

        for app_name in app_bundle_names:
            ## TODO: path for installing app bundles is hardcoded for now
            #app_path = os.path.join('/Applications', app_name + '.app')
            #cmd = ['mdls', app_path]

            #output, result = self.utilcmds.run_command(cmd)

            ## TODO(urgent): don't use the mdls module, it also runs on an OS X
            ## timer it seems. Meaning the applications meta data can't be read
            ## before a certain period of time.

            #for i in range(5):
            #    info_dict = self._separate_important_info(output)

            #    if info_dict:
            #        # We're good, we got the info. Break out and let this do
            #        # its thing.
            #        break

            #    # Give the OS some time to gather the data
            #    logger.debug("Sleeping for 5.")
            #    time.sleep(5)

            #if not info_dict:
            #    logger.error(
            #        "Could not get metadata for application: {0}"
            #        .format(app_name)
            #    )
            #    continue

            # TODO(urgent): stop hardcoding the path
            app_bundle_path = os.path.join('/Applications', app_name + '.app')

            info_dict = self._get_app_bundle_info(app_bundle_path)

            if not info_dict:
                logger.exception(
                    "Failed to gather metadata for: {0}".format(app_name)
                )

                continue

            app_inst = CreateApplication.create(
                info_dict['name'],
                info_dict['version'],
                '',  # description
                [],  # file_data
                [],  # dependencies
                '',  # support_url
                '',  # vendor_severity
                '',  # file_size
                '',  # vendor_id,
                '',  # vendor_name
                int(time.time()),  # install_date
                None,  # release_date
                True,  # installed
                "",  # repo
                "no",  # reboot_required
                "yes"  # TODO: check if app is uninstallable
            )

            app_instances.append(app_inst)

        return app_instances

    def install_supported_apps(self, install_data, update_dir=None):

        old_install_list = self.get_installed_applications()

        success = 'false'
        error = 'Failed to install application.'
        restart = 'false'
        #app_encoding = []
        apps_to_delete = []
        apps_to_add = []

        if not install_data.downloaded:
            error = 'Failed to download packages.'

            return InstallResult(
                success,
                error,
                restart,
                "{}",
                apps_to_delete,
                apps_to_add
            )

        if not update_dir:
            update_dir = settings.UpdatesDirectory

        try:
            pkgs = glob.glob(
                os.path.join(update_dir, "%s/*.pkg" % install_data.id)
            )
            dmgs = glob.glob(
                os.path.join(update_dir, "%s/*.dmg" % install_data.id)
            )

            if pkgs:
                success, error = self._install_third_party_pkg(pkgs)

                if success == 'true':
                    #app_encoding = self._get_app_encoding(install_data.name)

                    apps_to_add, apps_to_delete = \
                        self._get_apps_to_add_and_delete(old_install_list)

            elif dmgs:
                success, error, app_names = \
                    self._install_third_party_dmgs(dmgs)

                if success == 'true':

                    apps_to_add, apps_to_delete = \
                        self._get_apps_to_add_and_delete(old_install_list)

                    # OSX may not index these newly installed applications
                    # in time, therefore the information gathering has to be
                    # done manually.
                    if app_names:
                        newly_installed = \
                            self._create_app_from_bundle_info(app_names)

                        apps_to_add.extend(
                            [app.to_dict() for app in newly_installed]
                        )

                    # TODO(urgent): figure out how to get apps_to_delete
                    # for dmgs with app bundles

        except Exception as e:
            logger.error("Failed to install: {0}".format(install_data.name))
            logger.exception(e)

        return InstallResult(
            success,
            error,
            restart,
            "{}",
            apps_to_delete,
            apps_to_add
        )

    def install_custom_apps(self, install_data, update_dir=None):
        return self.install_supported_apps(install_data, update_dir)

    def install_agent_update(
            self, install_data, operation_id, update_dir=None):

        success = 'false'
        error = ''

        if update_dir is None:
            update_dir = settings.UpdatesDirectory

        if install_data.downloaded:
            update_dir = os.path.join(update_dir, install_data.id)
            dmgs = glob.glob(os.path.join(update_dir, "*.dmg"))

            path_of_update = [dmg for dmg in dmgs
                              if re.search(r'rvagent.*\.dmg', dmg.lower())]

            if path_of_update:
                path_of_update = path_of_update[0]

                updater = macupdater.MacUpdater()

                extra_cmds = ['--operationid', operation_id,
                              '--appid', install_data.id]

                success, error = updater.update(path_of_update, extra_cmds)

            else:
                logger.error(
                    "Could not find update in: {0}".format(update_dir)
                )
                error = 'Could not find update.'

        else:

            logger.debug("{0} was not downloaded. Returning false."
                         .format(install_data.name))

            error = "Update not downloaded."

        return InstallResult(
            success,
            error,
            'false',
            "{}",
            [],
            []
        )

    def _known_special_order(self, packages):
        """Orders a list of packages.

        Some packages need to be installed in a certain order.
        This method helps with that by ordering known packages.

        Args:
            - packages: List of packages to order.

        Returns:

            - A list of ordered packages.
        """

        # First implementation of this method is a hack. Only checks for
        # 'repair' because of known issues when trying to update Safari with
        # its two packages. The 'repair' package has to be installed first.

        ordered_packages = []

        for pkg in packages:

            if 'repair' in pkg.lower():

                ordered_packages.insert(0, pkg)

            else:

                ordered_packages.append(pkg)

        return ordered_packages

    def uninstall_application(self, uninstall_data):
        """ Uninstalls applications in the /Applications directory. """

        success = 'false'
        error = 'Failed to uninstall application.'
        restart = 'false'
        #data = []

        uninstallable_app_bundles = os.listdir('/Applications')

        app_bundle = uninstall_data.name + ".app"

        if app_bundle not in uninstallable_app_bundles:
            error = ("{0} is not an app bundle. Currently only app bundles are"
                     " uninstallable.".format(uninstall_data.name))

        else:

            uninstaller = Uninstaller()

            success, error = uninstaller.remove(uninstall_data.name)

        logger.info('Done attempting to uninstall app.')

        return UninstallResult(success, error, restart)

    def _add_update_data(self, name, restart):

        if restart == 'YES':
            restart = 'true'
        else:
            restart = 'false'

        self._macsqlite.add_update_data(name, restart)

    def _to_timestamp(self, d):
        """
        Helper method to convert datetime to a UTC timestamp.
        @param d: datetime.datetime object
        @return: a UTC/Unix timestamp string
        """
        return time.mktime(d.timetuple())

    def _download_catalogs(self):

        catalog_urls = [
            'http://swscan.apple.com/content/catalogs/index.sucatalog',
            'http://swscan.apple.com/content/catalogs/index-1.sucatalog',
            'http://swscan.apple.com/content/catalogs/others/index-leopard.merged-1.sucatalog',
            'http://swscan.apple.com/content/catalogs/others/index-leopard-snowleopard.merged-1.sucatalog',
            'http://swscan.apple.com/content/catalogs/others/index-lion-snowleopard-leopard.merged-1.sucatalog',
            'http://swscan.apple.com/content/catalogs/others/index-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog',
            'http://swscan.apple.com/content/catalogs/others/index-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog'
        ]

        for url in catalog_urls:
            filename = url.split('/')[-1]  # with file extension.
            try:
                urllib.urlretrieve(
                    url, os.path.join(self._catalog_directory, filename)
                )
            except Exception as e:
                logger.error("Could not download sucatalog %s." % filename)
                logger.exception(e)

    def _get_package_release_date(self, app_name):
        """ Checks the updates catalog (JSON) to get release date for app. """

        return self.updates_catalog.get_release_date(app_name)

    def _get_file_data(self, app_name):
        """ Checks the updates catalog (JSON) to get file_data for app. """

        return self.updates_catalog.get_file_data(app_name)

    def _get_reboot_required(self, app_name):
        return self.updates_catalog.get_reboot_required(app_name)

    def recreate_tables(self):
        pass  # self._macsqlite.recreate_update_data_table()
