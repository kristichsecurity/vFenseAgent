import os
import re
import urllib
import shutil
import hashlib

from utils import settings, logger, utilcmds, updater
from datetime import datetime
from rv.data.application import CreateApplication
from rv.rvsofoperation import RvError, InstallResult, UninstallResult


class FileDataKeys():
    uri = "file_uri"
    hash = "file_hash"
    name = "file_name"
    size = "file_size"


class PkgDictValues():
    name = 'Package'
    description = 'Description'
    description_en = 'Description-en'
    version = 'Version'
    file_size = 'Installed-Size'
    support_url = 'Homepage'
    uri = 'Filename'
    vendor_severity = 'Priority'
    dependencies = 'Depends'
    installed = 'Status'
    sha256 = 'SHA256'
    sha1 = 'SHA1'
    md5 = 'MD5sum'


class DebianHandler():
    PKG_STATUS_FILE = '/var/lib/dpkg/status'
    PKG_INSTALL_DATE_DIR = '/var/lib/dpkg/info/'
    APT_INSTALL_DIR = '/var/cache/apt/archives/'

    APT_GET_EXE = '/usr/bin/apt-get'
    APT_CACHE_EXE = '/usr/bin/apt-cache'

    INSTALLED_STATUS = 'install ok installed'

    PARSE_DATE_FORMAT = '%a, %d %b %Y %H:%M:%S %Z'

    def __init__(self):
        self.utilcmds = utilcmds.UtilCmds()

    def _apt_update_index(self):
        """Update index files."""

        logger.debug('Updating index.')

        cmd = [self.APT_GET_EXE, 'update']
        # TODO: if failure return an indication
        #result, err = self.utilcmds.run_command(cmd)
        self.utilcmds.run_command(cmd)

        logger.debug('Done updating index.')

    # TODO: find something better *************
    def _get_install_date(self, package_name):
        """Get the install date of a package.

        Checks the modification time of the "{package_name}.list"
        file for each package.

        """

        #TODO: other possible architectures that should be added?
        default_extension = '.list'
        amd64_extension = ':amd64.list'
        i386_extension = ':i386.list'

        #Try to obtain pkg installed-date
        package_path = self.PKG_INSTALL_DATE_DIR + package_name

        # TODO: test to see if this order of checking is corrrect.
        if os.path.exists(package_path + default_extension):
            package_path = package_path + default_extension
        elif os.path.exists(package_path + amd64_extension):
            package_path = package_path + amd64_extension
        elif os.path.exists(package_path + i386_extension):
            package_path = package_path + i386_extension
        else:
            return ''  # Could not find package

        return os.path.getmtime(package_path)

    def _get_release_date(self, uri):

        # TODO URGENT: figure out how to make it so that the whole
        # agent doesn't freeze up when user has a bad internet
        # connection

        if not uri:
            return ''

        try:
            unformatted_date = \
                urllib.urlopen(uri).info().getheaders('last-modified')[0]

            date_obj = datetime.strptime(
                unformatted_date, self.PARSE_DATE_FORMAT
            )
            release_date = date_obj.strftime(settings.DATE_FORMAT)

        except Exception as e:
            logger.error('Could not get release date.')
            logger.exception(e)
            return ''

        return release_date

    def _create_app_from_dict(self, package_dictionary, update_app=False):
        """Convert package dictionary into an instance of application.

        Arguments:

        update_app - Takes extra steps for update applications

        """

        app_name = package_dictionary.get(PkgDictValues.name, '')

        # TODO: change installed to status according to server specs
        installed = 'false'
        install_date = ''

        if not update_app:
            status = package_dictionary.get(PkgDictValues.installed, '')
            installed = status == self.INSTALLED_STATUS

            install_date = self._get_install_date(app_name)

        release_date = ''
        file_data = []
        dependencies = []

        if update_app:
            file_data = package_dictionary.get('file_data', [])

            if file_data:
                try:
                    release_date = \
                        self._get_release_date(
                            file_data[0].get(FileDataKeys.uri, '')
                        )

                except Exception as e:
                    logger.error('Failed to get release date for {0}'
                                 .format(app_name))
                    logger.exception(e)

        support_url = package_dictionary.get(PkgDictValues.support_url, '')

        repo = package_dictionary.get('repo', '')

        description = package_dictionary.get(PkgDictValues.description, '')
        if not description:
            # Try other possible description key
            description = \
                package_dictionary.get(PkgDictValues.description_en, '')

        application = \
            CreateApplication.create(
                app_name,
                package_dictionary.get(PkgDictValues.version, ''),
                description,
                file_data,
                dependencies,
                support_url,
                package_dictionary.get(PkgDictValues.vendor_severity, ''),
                package_dictionary.get(PkgDictValues.file_size, ''),
                "",  # Vendor id
                "",  # Vendor name
                install_date,
                release_date,
                installed,
                repo,
                "no",  # TODO(urgent): figure out if an app requires a  reboot
                "yes"  # TODO(urgent): figure out if an app is uninstallable
            )

        return application

    def _parse_info(self, info):
        info_separated = re.split(r'\n\s*?([A-Z][a-zA-Z0-9\s_-]+):\n? ', info)

        # Remove junk from beginning
        info_separated.pop(0)
        group_key_values = [[info_separated[i].strip(), info_separated[i+1]]
                            for i in range(0, len(info_separated), 2)]

        info_dictionary = dict(group_key_values)

        return info_dictionary

    def _parse_info_into_list(self, info):
        all_info = info.split('\n\n')
        all_info_list = []

        for info in all_info:
            #Regex pattern used in next split will not work for the very
            #first element unless a newline character is added to the
            #front of it. Reason: Splitting the info up with
            #re.split('\n\n') will remove the the '\n' that was there
            #in the first place. Unless it is the first line in the file,
            #which in that case we need to add a \n to the front anyways.
            regexable = '\n' + info
            data_dictionary = self._parse_info(regexable)

# TODO: Commenting out because of no need for parsing dependencies, currently
#            # Format dependencies properly
#            if PkgDictValues.dependencies in data_dictionary:
#
#                dep_string = data_dictionary[PkgDictValues.dependencies]
#                data_dictionary[PkgDictValues.dependencies] = \
#                    self.dep_cleaner.separate_dependency_string(dep_string)

            all_info_list.append(data_dictionary)

        # TODO: Getting junk in the end, why?
        return all_info_list

    def _parse_packages(self, info):
        all_info_list = self._parse_info_into_list(info)
        all_packages_dict = {}

        for data_dictionary in all_info_list:
            if PkgDictValues.name in data_dictionary:
                pkg_name = data_dictionary[PkgDictValues.name]
                all_packages_dict[pkg_name] = data_dictionary

        return all_packages_dict

    def _parse_file(self, file_name):
        """Parse the file and return a dictionary of all information.

        Ex: {'pkg_name' : {....}}
        """

        try:
            with open(file_name, 'r') as _file:
                content = _file.read()

                return self._parse_packages(content)

        except IOError as ioe:
            logger.error('Error while parsing file.')
            logger.exception(ioe)

    def _parse_repo_name(self, repo):
        """Get the repo name for the package."""

        repo_segments = repo.split(' ')

        return repo_segments[1]

    def _parse_packages_to_install(self, data):
        lines = data.split('\n')

        install_list = []
        for line in lines:
            if 'Inst' in line:
                try:
                    #package name comes right after Inst
                    #Example: "Inst {pkg-name} .....other data....."
                    update_package_name = line.split(' ')[1]

                    # New version comes right after old version
                    #Example: "Inst {name} [current-version] (new-version ....)
                    get_version_regex = r'.*\((\S+).*\)'
                    update_package_version = \
                        re.match(get_version_regex, line).group(1)

                    install_pkg = (update_package_name, update_package_version)

                    install_list.append(install_pkg)

                except AttributeError as e:
                    logger.error(
                        'Failed retrieving version for: ' + update_package_name
                    )
                    logger.exception(e)

        return install_list

    def check_available_updates(self):
        """
        Check apt for any packages in need of update(called upgrade in apt-get)

        Return:
        update_package_list -- list of the package names in need of update.
        """

        # DO NOT REMOVE -s. Upgrade is simulated to parse out
        # the packages that need to be updated.
        cmd = [self.APT_GET_EXE, '-s', 'upgrade']
        result, err = self.utilcmds.run_command(cmd)

        return self._parse_packages_to_install(result)

    def _get_installed_packages(self):
        """Return all of the installed packages in a dictionary.

        Ex: {'pkg': {...data...}}
        """

        all_pkgs_dict = self._parse_file(self.PKG_STATUS_FILE)

        installed_pkgs_dict = {}
        for pkg in all_pkgs_dict:

            status = all_pkgs_dict[pkg].get(PkgDictValues.installed, '')
            if status == self.INSTALLED_STATUS:
                installed_pkgs_dict[pkg] = all_pkgs_dict[pkg]

        return installed_pkgs_dict

    def _parse_repo_from_cache(self, pkg_name, version):
        try:
            results, err = self.utilcmds.run_command(
                [self.APT_CACHE_EXE, 'madison', pkg_name])

            if err:
                raise Exception(err)

            repo_options = [x for x in results.split('\n') if x != '']

            for option in repo_options:
                option = option.split('|')
                option = [x.strip() for x in option]

                if option[1] == version:
                    return option[2]

        except Exception as e:
            logger.error(
                'error with: ' + pkg_name + ' when running apt-cache madison'
            )
            logger.exception(e)

            return ''

    def _get_file_data(self, data_dictionary, repo):
        """ Create a dictionary that contains name, uri, hash, size, and
            pkg_type.

        file_data format:
        "file_data":[
                      { "file_name"      : name of package
                        "file_uri"       : uri here
                        "file_hash"      : sha256
                        "file_size"      : size in kb's
                        ## "pkg_type"  : primary or dependency
                      }
                    ]
        """

        # TODO: implement a for loop for the possibility of multiple uri's

        file_data = []

        # uri
        uri = data_dictionary.get(PkgDictValues.uri, '')
        if uri:
            hostname = repo.split(' ')[0]
            uri = hostname + data_dictionary[PkgDictValues.uri]

        # name
        name = uri.split('/')[-1]

        # hash
        pkg_hash = data_dictionary.get(PkgDictValues.sha256, '')

        if not pkg_hash:
            pkg_hash = data_dictionary.get(PkgDictValues.sha1, '')

        if not pkg_hash:
            pkg_hash = data_dictionary.get(PkgDictValues.md5, '')

        # size
        size = data_dictionary.get('Size', '')

        try:
            size = int(size)
        except Exception as e:
            logger.error("Failed to cast file_size to int.")
            logger.exception(e)

            # If for whatever reason it fails to convert
            size = ''

        # Package is marked as primary, the dependencies added
        # to file_data are marked as dependency.
        #pkg_type = 'primary'

        file_data = [{FileDataKeys.name: name,
                      FileDataKeys.uri: uri,
                      FileDataKeys.hash: pkg_hash,
                      FileDataKeys.size: size}]
                      #'pkg_type': pkg_type}]

        return file_data

    def get_available_updates_data(self, package_list):
        update_pkg_data = {}

        for package in package_list:
            pkg_name = package[0]
            pkg_version = package[1]

            available_info, err = self.utilcmds.run_command(
                [self.APT_CACHE_EXE, 'show', pkg_name])

            package_repo = self._parse_repo_from_cache(pkg_name, pkg_version)

            # Includes new package and old packages
            package_options = self._parse_info_into_list(available_info)

            for option in package_options:
                option_version = option.get(PkgDictValues.version, '')

                if option_version == pkg_version:
                    update_pkg_data[pkg_name] = option

                    # add the repo
                    update_pkg_data[pkg_name]['repo'] = \
                        self._parse_repo_name(package_repo)

                    # add file_data
                    update_pkg_data[pkg_name]['file_data'] = \
                        self._get_file_data(option, package_repo)

        return update_pkg_data

    def _get_app_dependencies(self, name):
        cmd = [self.APT_GET_EXE, '-s', 'install', name]

        result, err = self.utilcmds.run_command(cmd)

        dep_list = []
        dependencies = self._parse_packages_to_install(result)

        if dependencies:
            dependencies = [dep for dep in dependencies if dep[0] != name]

            for dep in dependencies:
                root = {}
                root['name'] = dep[0]
                root['version'] = dep[1]
                root['app_id'] = \
                    hashlib.sha256("{0}{1}".format(dep[0], dep[1])).hexdigest()

                dep_list.append(root)

        return dep_list

    def _append_file_data(self, app, update_apps):
        # Allows for faster and easier searching
        updates = {updapp.name: updapp for updapp in update_apps}

        for dep in app.dependencies:
            if dep['name'] in updates:
                update_app = updates[dep['name']]

                if dep['version'] == update_app.version:
                    # Coyping file_data[0] with dict(), avoiding reference.
                    # file_data[0] corresponds to the file data of the app
                    # itself, not its dependencies.
                    append_dict = dict(update_app.file_data[0])
                    app.file_data.append(append_dict)

    def get_available_updates(self):
        """Get application instances of the packages in need of update.
        """
        logger.info('Getting available updates.')

        self._apt_update_index()

        #installed_packages = self._get_installed_packages()
        update_packages = self.check_available_updates()

        update_pkgs_data = self.get_available_updates_data(update_packages)

        apps = []

        # For logging
        i = 1
        amount_of_packages = len(update_packages)

        for package in update_packages:
            pkg_name = package[0]

            try:
                app = self._create_app_from_dict(
                    update_pkgs_data[pkg_name], True
                )

                # Slow, but as accurate as apt-get,
                # returns a list of dictionaries which includes all deps
                # [{'name': .. , 'version' : .. , 'app_id' : ..}]
                app.dependencies = self._get_app_dependencies(app.name)

                apps.append(app)

                logger.debug(
                    'Done getting info for {0} out of {1}. Package name: {2}'
                    .format(i, amount_of_packages, app.name)
                )

                i += 1

            except Exception as e:
                logger.error('get_available_updates failed for: ' + pkg_name)
                logger.exception(e)

        # Append all dependencies' file_data to app's file_data.
        # Must be done after getting all apps.
        for app in apps:
            self._append_file_data(app, apps)

        return apps

    def get_installed_updates(self):
        """rvplugin calls this function, but only meant for Mac."""
        return []

    def _get_installed_app(self, name):
        installed_packages = self._get_installed_packages()
        pkg_dict = installed_packages.get(name, {})

        if not pkg_dict:
            return CreateApplication.null_application()

        return self._create_app_from_dict(pkg_dict)

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

    def get_installed_applications(self):
        """
        Return a list of the installed packages as Application instances.
        """
        installed_packages = self._get_installed_packages()

        apps = []
        for package in installed_packages:
            app = self._create_app_from_dict(installed_packages[package])

            if app:
                apps.append(app)

        #if strip_deps:
        #    # Mutates the dependencies attribute
        #    self.dep_cleaner.clean_app_dependencies(apps)

        return apps

    def _apt_clean(self):
        logger.debug('Running apt-get clean.')

        clean_cmd = [self.APT_GET_EXE, 'clean']

        try:
            self.utilcmds.run_command(clean_cmd)

            logger.debug('Cleaned /var/cache/apt/archives.')

        except Exception as e:
            logger.error('Failed to clean /var/cache/apt/archives.')
            logger.exception(e)

    def _apt_install(self, package_name):
        logger.debug('Installing {0}'.format(package_name))

        install_command = [self.APT_GET_EXE, 'install', '-y', package_name]

        #TODO: figure out if restart needed
        restart = 'false'

        # TODO: parse out the error, if any
        try:
            result, err = self.utilcmds.run_command(install_command)

            if err:
                # Catch non-error related messages
                if 'reading changelogs' in err.lower():
                    pass
                else:
                    raise Exception(err)

        except Exception as e:
            logger.error('Faled to install {0}'.format(package_name))
            logger.exception(e)

            return 'false', str(e), restart

        logger.debug('Done installing {0}'.format(package_name))

        return 'true', '', restart

    def _move_pkgs_to_apt_dir(self, packages_dir):
        log_message = ('moving packages in {0} *** to *** {1}'
                       .format(packages_dir, self.APT_INSTALL_DIR))

        logger.debug(log_message)

        try:

            for pkg in os.listdir(packages_dir):
                destination = os.path.join(self.APT_INSTALL_DIR, pkg)

                # TODO: copy vs move
                shutil.copy(os.path.join(packages_dir, pkg), destination)

            logger.debug('Done moving packages.')

            return ''

        except Exception as e:
            logger.error('Failed {0}'.format(log_message))
            logger.exception(e)

        return 'Failed {0}'.format(log_message)

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

    def _get_apps_to_add_and_delete(self, old_install_list):
        new_install_list = self.get_installed_applications()

        apps_to_delete = self._get_apps_to_delete(
            old_install_list, new_install_list
        )

        apps_to_add = self._get_apps_to_add(
            old_install_list, new_install_list
        )

        return apps_to_add, apps_to_delete

    def install_update(self, install_data, update_dir=None):
        logger.debug('Received install_update call.')

        old_install_list = self.get_installed_applications()

        success = 'false'
        error = RvError.UpdatesNotFound
        restart = 'false'
        app_encoding = CreateApplication.null_application().to_dict()
        apps_to_delete = []
        apps_to_add = []

        if not update_dir:
            update_dir = settings.UpdatesDirectory

        packages_dir = os.path.join(update_dir, install_data.id)
        moving_error = self._move_pkgs_to_apt_dir(packages_dir)

        if not moving_error:
            success, error, restart = self._apt_install(install_data.name)

            if success == 'true':

                app = self._get_installed_app(install_data.name)
                app_encoding = app.to_dict()

                apps_to_add, apps_to_delete = \
                    self._get_apps_to_add_and_delete(old_install_list)

        else:
            error = moving_error

        # TODO(urgent): should I apt-get clean here or in rv_plugin?

        return InstallResult(
            success,
            error,
            restart,
            app_encoding,
            apps_to_delete,
            apps_to_add
        )

    def install_supported_apps(self, install_data, update_dir=None):
        old_install_list = self.get_installed_applications()

        success = 'false'
        error = 'Failed to install application.'
        restart = 'false'
        app_encoding = "{}"
        apps_to_delete = []
        apps_to_add = []

        if not install_data.downloaded:
            error = 'Failed to download packages.'

            return InstallResult(
                success,
                error,
                restart,
                app_encoding,
                apps_to_delete,
                apps_to_add
            )

        if not update_dir:
            update_dir = settings.UpdatesDirectory

        try:
            update_dir = os.path.join(update_dir, install_data.id)
            success, error = self._dpkg_install(update_dir)

            if success == 'true':
                apps_to_add, apps_to_delete = \
                    self._get_apps_to_add_and_delete(old_install_list)

        except Exception as e:
            error = ("Failed to install updates from: {0}"
                     .format(install_data.name))

            logger.error(error)
            logger.exception(e)

        return InstallResult(
            success,
            error,
            restart,
            app_encoding,
            apps_to_delete,
            apps_to_add
        )

    def install_custom_apps(self, install_data, update_dir=None):
        return self.install_supported_apps(install_data, update_dir)

    def install_agent_update(
        self, install_data, operation_id, update_dir=None
    ):
        success = 'false'
        error = ''

        if update_dir is None:
            update_dir = settings.UpdatesDirectory

        if install_data.downloaded:
            update_dir = os.path.join(update_dir, install_data.id)

            dir_files = [file for file in os.listdir(update_dir)
                         if re.search("vfagent*", file.lower())]

            update_file = [file for file in dir_files if '.' not in file]

            if update_file:
                path_of_update = os.path.join(update_dir, update_file[0])

                agent_updater = updater.Updater()

                extra_cmds = ['--operationid', operation_id,
                              '--appid', install_data.id]

                success, error = agent_updater.update(
                    path_of_update, extra_cmds
                )

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

    def _dpkg_install(self, update_dir=None):
        """Install an update or install a new package.

        If an update directory is given, it must be made sure that
        the directory contains all of the dependencies for ALL of the
        packages inside the directory.
        """

        if update_dir:
            install_command = ['dpkg', '-i',  '-R', update_dir]

            try:
                result, err = self.utilcmds.run_command(install_command)

                if err:
                    raise Exception(err)

                logger.info(
                    ('debhandler.py/_dpkg_install: '
                     'Installed all packages in: ') + update_dir)

                return 'true', ''

            except Exception as e:
                logger.error(
                    ('debhandler.py/_dpkg_install: '
                     'Failed to install packages in: ') + update_dir)

                return 'false', str(e)
        else:
            logger.info(
                'debhandler.py/_dpkg_install: No directory provided.')

        return 'false', 'Update dir: ' + update_dir

    def _apt_purge(self, package_name):
        purged = 0

        purge_command = [self.APT_GET_EXE, 'purge', '-y', package_name]

        try:
            result, err = self.utilcmds.run_command(purge_command)

            if err:
                raise Exception(err)

            found = re.search('\\d+ to remove', result)
            if found:
                amount_purged = found.group().split(' ')[0]
                purged = int(amount_purged)

            if purged > 0:
                logger.debug(
                    'Successfuly removed {0} packages.'.format(purged)
                )

                return 'true', ''
            else:
                logger.info('No packages were removed.')

                return 'false', 'No packages removed.'

        except Exception as e:
            logger.error('Problem while uninstalling package: ' + package_name)
            logger.exception(e)

            return 'false', str(e)

    def uninstall_application(self, uninstall_data):
        """Uninstall packages provided in operation uninstall list"""

        success = 'false'
        error = 'Failed to uninstall application.'
        restart = 'false'

        success, error = self._apt_purge(uninstall_data.name)

        # TODO: check if restart is needed

        return UninstallResult(success, error, restart)
