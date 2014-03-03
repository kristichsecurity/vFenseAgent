import os
import re
import glob
import hashlib
import subprocess

from serveroperation.sofoperation import *
from utils import logger, updater, utilcmds

from rv.data.application import CreateApplication
from rv.rvsofoperation import InstallResult, UninstallResult, RvOperationKey
from rv.distro.redhat import yum
from rv.distro.redhat.yum.repos import RepoData, get_primary_file


class RpmOpHandler():

    def __init__(self):
        self.utilcmds = utilcmds.UtilCmds()

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

    def _get_installed_app(self, name, install_list):
        for app in install_list:
            if app.name == name:
                return app

        return CreateApplication.null_application()

    def _yum_local_update(self, package_name, packages_dir):
        logger.debug('Installing {0}'.format(package_name))
        #TODO: figure out if restart needed
        restart = 'false'

        rpms = glob.glob(os.path.join(packages_dir, '*.rpm'))

        cmd = [yum.yum_cmd, '--nogpgcheck', 'localupdate', '-y']
        cmd.extend(rpms)

        try:
            output, error = self.utilcmds.run_command(cmd)

            if error:
                raise Exception(error)

        except Exception as e:
            logger.error('Faled to install {0}'.format(package_name))
            logger.exception(e)

            return 'false', str(e), restart

        logger.debug('Done installing {0}'.format(package_name))

        return 'true', '', restart

    def install_update(self, install_data, update_dir=None):
        logger.debug('Received install_update call.')

        old_install_list = self.get_installed_applications()

        success = 'false'
        error = ''
        restart = 'false'
        app_encoding = CreateApplication.null_application().to_dict()
        apps_to_delete = []
        apps_to_add = []

        if not update_dir:
            update_dir = settings.UpdatesDirectory

        if install_data.downloaded:

            packages_dir = os.path.join(update_dir, install_data.id)
            success, error, restart = self._yum_local_update(
                install_data.name, packages_dir
            )

            if success == 'true':

                new_install_list = self.get_installed_applications()

                app = self._get_installed_app(
                    install_data.name, new_install_list
                )
                app_encoding = app.to_dict()

                apps_to_add, apps_to_delete = self._get_apps_to_add_and_delete(
                    old_install_list, new_install_list
                )

        else:
            logger.debug("Downloaded = False for: {0}"
                         .format(install_data.name))
            error = "Failed to download packages."

        return InstallResult(
            success,
            error,
            restart,
            app_encoding,
            apps_to_delete,
            apps_to_add
        )

    def _yum_update(self, package_name):
        logger.debug('Updating: {0}'.format(package_name))

        #TODO: figure out if restart needed after update
        restart = 'false'

        try:
            cmd = [yum.yum_cmd, 'update', '-y', package_name]
            result, err = self.utilcmds.run_command(cmd)

            if err:
                if 'warning:' in err:
                    pass
                else:
                    raise Exception(err)

        except Exception as e:
            logger.error('Faled to update {0}'.format(package_name))
            logger.exception(e)

            return 'false', str(e), restart

        logger.debug('Done updating {0}'.format(package_name))

        return 'true', '', restart

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
            update_dir = os.path.join(update_dir, '*.rpm')
            success, error = self._rpm_install(update_dir)

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

    def _rpm_install(self, update_dir):
        install_command = ['/bin/rpm', '-U', update_dir]

        try:
            result, err = self.utilcmds.run_command(install_command)

            if err:
                raise Exception(err)

            logger.info(
                ('rhelhandler.py/_rpm_install: '
                 'Installed all packages in: ') + update_dir)

            return 'true', ''

        except Exception as e:
            logger.error(
                ('rhelhandler.py/_rpm_install: '
                 'Failed to install packages in: ') + update_dir)

            return 'false', str(e)

        else:
            logger.info(
                'rhelhandler.py/_rpm_install: No directory provided.')

        return 'false', 'Update dir: ' + update_dir

    def install_custom_apps(self, install_data, update_dir=None):
        return self.install_supported_apps(install_data, update_dir)

    def install_agent_update(self, install_data, operation_id, update_dir=None):
        success = 'false'
        error = ''

        if update_dir is None:
            update_dir = settings.UpdatesDirectory

        if install_data.downloaded:
            update_dir = os.path.join(update_dir, install_data.id)

            tar_files = glob.glob(os.path.join(update_dir, "*.tar*"))

            path_of_update = [tar for tar in tar_files
                              if re.search(r'rvagent.*\.tar.*', tar.lower())]

            if path_of_update:
                path_of_update = path_of_update[0]

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

    def uninstall_application(self, uninstall_data):
        success = 'false'
        error = 'Failed to uninstall application.'
        restart = 'false'

        success, error = self._yum_remove(uninstall_data.name)

        # TODO: check if restart is needed

        return UninstallResult(success, error, restart)

    def _yum_remove(self, package_name):
        remove_cmd = [yum.yum_cmd, 'remove', '-y', package_name]

        try:
            output, err = self.utilcmds.run_command(remove_cmd)

            if err:
                raise Exception(err)

            return 'true', ''

        except Exception as e:
            logger.error(
                "Error while removing application: {0}".format(package_name)
            )
            logger.exception(e)

            return 'false', str(e)

    def _get_dependencies(self, name, version, release, arch):
        #yum_update = yum.YumUpdate(name, version, release, arch, '')

        # TODO: architecture keeps giving problems. Duplicate
        # packages in available updates with different architectures, but
        # when checking yum update {package} you HAVE to have the right
        # architecture.
        yum_update = yum.YumUpdate(name, version, release, '', '')
        yum_deps = []

        try:
            yum_deps = yum.get_needed_dependencies(yum_update)
        except Exception as e:
            logger.error("Failed to get depenencies for: {0}".format(name))
            logger.exception(e)

        # When an error occurs in get_needed_dependencies (not an exception)
        # it might set yum_deps to None. Therefore an error occurs when
        # trying to iterate over it.
        if not yum_deps:
            return []

        dep_list = []
        for dep in yum_deps:
            version = dep.version
            if dep.release:
                version = '{0}-{1}'.format(version, dep.release)

            dep_dict = {}
            dep_dict['name'] = dep.name
            dep_dict['version'] = version
            dep_dict['app_id'] = hashlib.sha256("{0}{1}".format(
                dep.name, dep.version)
            ).hexdigest()

            # TODO: find a solution. Getting duplicates of package
            # just different architecture. Should we only be listing one?
            # or both?
            if dep_dict not in dep_list:
                dep_list.append(dep_dict)

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
        """Gets available updates, as Appliation instances, through yum.

        Returns:

            - A list of Applications.

        """

        logger.info('Getting available updates.')

        updates = []

        try:

            yum.renew_repo_cache()
            updates_available = yum.list_updates()
            rd = RepoData()
            primary_files = {}

            # For logging
            i = 1
            total = len(updates_available)

            for update in updates_available:

                application = None

                try:

                    #deps = yum.get_needed_dependencies(update)

                    repo = rd.get_repo(update.repo)

                    if not repo.id:

                        logger.info(
                            "No primary.xml data for {0}. Skipping."
                            .format(update.name)
                        )

                        continue

                    if repo.id not in primary_files:

                        primary_files[repo.id] = get_primary_file(repo.id, rd)

                    meta_packages = (
                        primary_files[repo.id].find_packages(update.name)
                    )

                    mp = None
                    for pkg in meta_packages:

                        if (
                            pkg.name == update.name
                            and pkg.version == update.version
                            and pkg.release == update.release
                            and pkg.arch == update.arch
                        ):

                            mp = pkg

                            #file_data = self._create_file_data(
                            #    mp,
                            #    deps,
                            #    repo,
                            #    primary_files,
                            #    rd
                            #)
                            file_data = self._create_file_data(mp, repo)

                            dependencies = self._get_dependencies(
                                mp.name,
                                mp.version,
                                mp.release,
                                mp.arch
                            )

                            application = CreateApplication.create(
                                mp.name,
                                mp.complete_version,
                                mp.description,  # description
                                file_data,  # file_data
                                dependencies,  # dependencies
                                mp.url,  # support_url
                                '',  # vendor_severity
                                mp.size,  # file_size
                                '',  # vendor_id,
                                mp.vendor,  # vendor_name
                                None,  # install_date
                                mp.release_date,  # release_date
                                False,  # installed
                                repo.name,  # repo
                                "no",  # reboot_required
                                "yes"  # TODO: Is app uninstallable?
                            )

                            break

                except Exception as e:

                    logger.error("Could not get available update. Skipping.")
                    logger.exception(e)

                if application:

                    updates.append(application)
                    logger.debug(application)

                logger.debug("{0} out of {1} finished.".format(i, total))
                i += 1

            # Append all dependencies' file_data to app's file_data.
            # Must be done after getting all apps.
            for update in updates:
                self._append_file_data(update, updates)

        except Exception as e:

            logger.error("Could not get available updates.")
            logger.exception(e)

        logger.info('Done.')
        return updates

    def get_installed_updates(self):
        """No implementation necessary.

        No such thing as 'updates installed' for RPMs. Equivalent data
        would be found in installed applications.

        Returns:

            - An empty list.
        """

        return []

    def get_installed_applications(self):
        """Gets installed RPM-based applications.

        Returns:

            - A list of Applications.

        """
        logger.info('Getting installed packages.')

        installed_apps = []

        # Get the data in a nice, easy, parsable format.
        query_separator = '**!TOPPATCH!**'
        query_format = (
            '"%{{NAME}}{0}%{{VERSION}}-%{{RELEASE}}{0}%{{INSTALLTIME}}'
            '{0}%{{BUILDTIME}}{0}%{{SIZE}}{0}%{{VENDOR}}{0}'
            '%{{URL}}{0}%{{DESCRIPTION}}"'.format(query_separator)
        )

        try:

            process = subprocess.Popen(
                ['rpm', '-qa'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            output, _stderr = process.communicate()
            output = (
                output
                .decode(settings.default_decoder)
                .encode(settings.default_encoder)
            )

            installed_list = output.splitlines()

            for app in installed_list:

                try:

                    rpm_query = \
                        ['rpm', '-q', app, '--queryformat', query_format]

                    process = subprocess.Popen(
                        rpm_query, stdout=subprocess.PIPE
                    )
                    output, _stderr = process.communicate()
                    output = (
                        output
                        .decode(settings.default_decoder)
                        .encode(settings.default_encoder)
                    )

                    app_info = output.split(query_separator)

                    # Little bit of cleanup
                    name = app_info[RpmQueryInfo.Name]
                    if name.startswith('"'):
                        name = name[1:]

                    description = app_info[RpmQueryInfo.Description]
                    description = description.replace('\n', ' ')
                    if description.endswith('"'):
                        description = description[0:-1]
                    #######################

                    application = CreateApplication.create(
                        name,  # app name
                        app_info[RpmQueryInfo.Version],  # app version
                        description,  # app description
                        [],  # file_data
                        [],  # dependencies
                        app_info[RpmQueryInfo.Url],  # support url
                        '',  # vendor_severity
                        app_info[RpmQueryInfo.Size],  # app size
                        '',  # vendor_id
                        app_info[RpmQueryInfo.Vendor],  # app's vendor
                        app_info[RpmQueryInfo.InstallDate],  # install_date
                        app_info[RpmQueryInfo.ReleaseDate],  # release_date
                        True,  # installed
                        '',  # repo
                        'no',  # reboot_required
                        'yes'  # TODO: check if app is uninstallable
                    )

                except Exception as e:
                    logger.error(
                        "Error while checking installed application. Skipping"
                    )
                    logger.exception(e)
                    application = None

                if application:

                    installed_apps.append(application)

        except Exception as e:
            logger.error("Error while checking installed applications.")
            logger.exception(e)

        logger.info('Done.')

        return installed_apps

    @staticmethod
    def _create_file_data(main_package, repo):
    #def _create_file_data(main_package, deps, repo,
    #                      primary_data=None, repo_data=None):

        """Create the file data for the main package.

        Args:

            - main_package: A MetaPackage instance for the main
                package to create file data for.

            - deps: A list of YumUpdate describing the main package
                dependencies.

            - repo: A Repo instance of the main package's repo.

            - primary_data: A dict of PrimayXml instances index by the
                respective repo's unique ID.

            - repo_data: a RepoData instance.

        Returns:

            - A python dict according to SoF Format for file data.

        """

        file_data = []
        file_uri = os.path.join(repo.url, main_package.location)
        file_size = main_package.size

        # name
        file_name = file_uri.split('/')[-1]

        try:
            file_size = int(file_size)
        except Exception as e:
            logger.error(
                "Failed to cast file_size to int. {0}"
                .format(main_package.name)
            )
            logger.exception(e)

            # If for whatever reason it fails to convert
            file_size = ''

        main = {
            RvOperationKey.FileName: file_name,
            RvOperationKey.FileUri: file_uri,
            RvOperationKey.FileHash: main_package.hash,
            RvOperationKey.FileSize: file_size,
            #RvOperationKey.PackageType: 'primary'
        }

        file_data.append(main)

        #dep_files = []
        #for dep in deps:

        #    try:

        #        if primary_data[dep.repo]:

        #            dep_primary = primary_data[dep.repo]

        #            meta_packages = dep_primary.find_packages(dep.name)

        #            mp = None
        #            for pkg in meta_packages:

        #                if (
        #                    pkg.name == dep.name
        #                    and pkg.version == dep.version
        #                    and pkg.release == dep.release
        #                    and pkg.arch == dep.arch
        #                ):
        #                    mp = pkg

        #                    r = repo_data.get_repo(dep.repo)

        #                    f = {
        #                        RvOperationKey.FileUri: os.path.join(
        #                            r.url, mp.location
        #                        ),
        #                        RvOperationKey.FileHash: main_package.hash,
        #                        #RvOperationKey.PackageType: 'dependency'
        #                    }

        #                    dep_files.append(f)
        #                    break

        #    except Exception as e:

        #        logger.error(
        #            "Could not find data for dependecy {0}. Skipping"
        #            .format(dep.name)
        #        )
        #        logger.exception(e)

        #file_data.extend(dep_files)

        return file_data


class RpmQueryInfo():

    Name = 0
    Version = 1
    InstallDate = 2
    ReleaseDate = 3
    Size = 4
    Vendor = 5
    Url = 6
    Description = 7
