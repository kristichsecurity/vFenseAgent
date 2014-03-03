## TODO(remove): remove or leave commented
#import sys
#sys.path.append("../../../src")
#sys.path.append("../../")
#import json
##########################################

import os
import re
import time
import hashlib
import subprocess

from utils import logger, settings, utilcmds

from rv.distro.redhat import yum
from rv.operationhandler.rpmhandler import RpmOpHandler

from rv.data.application import CreateApplication
from rv.rvsofoperation import InstallResult, UninstallResult


class PkgKeys():

    name = 'Name'
    version = 'Version'
    release_date = 'Buildtime'
    description = 'Description'

    arch = 'Arch'
    epoch = 'Epoch'
    release = 'Release'

    lookup_name = 'severity_lookup_name'
    full_version = 'full_version'


class YumParse():

    def _clean_up_info_updates(self, updates_data):
        packages_data = updates_data.split('\n\n')

        # The first element has cruft that needs to be removed
        start_at = 'Updated Packages'
        packages_data[0] = packages_data[0].splitlines()
        avoid_till = packages_data[0].index(start_at) + 1
        packages_data[0] = '\n'.join(packages_data[0][avoid_till:])

        return packages_data

    def _split_package_data(self, package_data):
        """
        Takes the raw info data for ONE package and cleans/makes
        it easily parsable by having the keys on left of : and the value on
        the right for each string. Each string in the list returned
        represents a key which has a value.

        Example:
            'Name       : NetworkManager'
            'Arch       : x86_64'
            'Epoch      : 1'
            'Version    : 0.7.0'
        """
        lines = package_data.splitlines()

        split = []
        for line in lines:
            if not re.match('^\w', line):
                clean_line = line.split(':')[1].strip()

                if split:
                    split[-1] = split[-1] + ' ' + clean_line

            else:
                split.append(line)

        return split

    def _dict_from_split_pkg_data(self, package_data_list):
        pkg_dict = {}
        for line in package_data_list:
            key, value = [x.strip() for x in line.split(':', 1)]
            pkg_dict[key] = value

        if PkgKeys.release_date in pkg_dict:
            release_date = time.strptime(pkg_dict[PkgKeys.release_date])
            release_date = time.strftime('%s', release_date)
            pkg_dict[PkgKeys.release_date] = release_date

        return pkg_dict

    def _get_severity_lookup_name(self, pkg_dict):
        """
        The name is composed of {name}-{epoch}:{version}-{release}.{arch}
        but not always.

        ** Important **:

            Avoiding returning the arch in the name because it causes problems
            when looking up a package in the security data from yum.

            Currently when we parse for the available updates from
            "yum info updates"
            yum shows duplicate packages but with i386 and x86_64
            architectures. The name is all we currently need, so either get
            chosen. However, "yum list-security", looks to only show
            for one specific architecture. Therefore we might not get a match
            due to having chosen whichever architecture.
        """
        security_lookup_name = pkg_dict[PkgKeys.name] + '-'

        epoch = pkg_dict.get(PkgKeys.epoch, '')
        version = pkg_dict.get(PkgKeys.version, '')
        release = pkg_dict.get(PkgKeys.release, '')
        #arch = pkg_dict.get(PkgKeys.arch, '')

        if epoch:
            security_lookup_name += '{0}:'.format(epoch)

        if version:
            security_lookup_name += '{0}-'.format(version)

        if release:
            security_lookup_name += '{0}'.format(release)
            #security_lookup_name += '{0}.'.format(release)
        #else:
        #    security_lookup_name[-1] = '.'

        #if arch:
        #    security_lookup_name += '{0}'.format(arch)
        #else:
        #    # Remove the trailing dot.
        #    security_lookup_name = security_lookup_name[:-1]

        return security_lookup_name

    def parse_info_updates(self, updates_data):
        """
        Parses the data provided from the command:
        "yum info updates -v"

        Returns:
            A list of dictionaries for each package.
        """
        #sys_arch = systeminfo.system_architecture()

        clean_pkg_data = self._clean_up_info_updates(updates_data)

        package_dicts = {}
        for pkg_data in clean_pkg_data:
            split_data = self._split_package_data(pkg_data)

            pkg_dict = self._dict_from_split_pkg_data(split_data)
            pkg_name = pkg_dict.get(PkgKeys.name, '')

            if not pkg_name:
                logger.warning(
                    "No name for dict: {0}".format(pkg_dict)
                )
                continue

            # Avoid duplicate dicts
            if pkg_name in package_dicts:
                continue

            pkg_dict[PkgKeys.lookup_name] = \
                self._get_severity_lookup_name(pkg_dict)

            full_version = pkg_dict[PkgKeys.version]
            if pkg_dict.get(PkgKeys.release, ''):
                full_version = '{0}-{1}'.format(
                    full_version, pkg_dict[PkgKeys.release]
                )

            pkg_dict[PkgKeys.full_version] = full_version

            package_dicts[pkg_name] = pkg_dict

            # Can't discriminate by arch because x86_64 arch machines
            # can have i386 packages installed, which need updates.
            # pkg_arch = pkg_dict.get(PkgKeys.arch, 'noarch')

            # if pkg_arch == 'noarch' or pkg_arch == sys_arch:
            #     package_dicts.append(pkg_dict)

        return package_dicts.values()

    def _get_matching_severity(self, severity):
        """
        Gets the corresponding TopPatch severity for each package.

        Returns:
            security -> Critical
            bugfix -> Recommended
            enhancement -> Optional
        """

        if severity == 'security':
            return 'Critical'
        if severity == 'bugfix':
            return 'Recommended'

        return 'Optional'

    def parse_pkg_severity(self, security_data):
        """
        Parses the data provided from the command:
        "yum list-security"

        Returns:
            A dictionary with specific names as keys severity as value.

            Example:
                {'quota-1:3.13-8.el5.x86_64': 'critical',
                 'comps-extras-11.4-1.noarch': 'recommended',
                 'coolkey-1.1.0-15.el5.i386': 'optional'}

            The key is composed of {name}-{epoch}:{version}.{release}.{arch}
            but not always as seen in examples.

            ** Important **:
            May contain Junk as keys, please use keys to match against only.

            Also, currently stripping out {arch}, see _get_severity_lookup_name
            for reason.
        """

        severity_dict = {}
        for line in security_data.splitlines():
            split = line.split()

            if len(split) != 3:
                continue

            # Removing arch if found, see method documentation.
            key_name = split[2]
            key_split = key_name.split('.')
            if key_split[-1] in ['x86_64', 'i386', 'noarch']:
                key_name = '.'.join(key_split[:-1])

            #vendor_severity = self._get_matching_severity(split[1])
            vendor_severity = split[1]

            severity_dict[key_name] = vendor_severity

        return severity_dict


class RhelOpHandler(RpmOpHandler):

    def __init__(self):
        self.utilcmds = utilcmds.UtilCmds()

        self._install_security_plugin()
        self.yum_parse = YumParse()

    def _install_security_plugin(self):
        logger.debug("Attempting to install yum-plugin-security.")
        cmd = [yum.yum_cmd, 'install', '-y', 'yum-plugin-security']
        output, err = self.utilcmds.run_command(cmd)

        # TODO: should agent continue if failure?
        if err:
            logger.error("Failed to install yum security plugin.")

    def get_available_updates(self):
        logger.debug('Getting available updates.')

        try:
            logger.debug("Renewing repo cache.")
            yum.renew_repo_cache()
            logger.debug("Done renewing repo cache.")

            logger.debug("Getting list of available updates.")
            cmd = [yum.yum_cmd, 'info', 'updates', '-v']
            output, err = self.utilcmds.run_command(cmd)
            if err:
                raise Exception(err)

            avail_updates = self.yum_parse.parse_info_updates(output)
            logger.debug("Done getting list of available updates.")

            logger.debug("Getting severity of packages.")
            cmd = [yum.yum_cmd, 'list-security']
            output, err = self.utilcmds.run_command(cmd)
            if err:
                logger.error("Failed to get package severities.")
                logger.exception(err)
                severity_of_pkgs = {}
            else:
                severity_of_pkgs = self.yum_parse.parse_pkg_severity(output)
                logger.debug("Done getting severity of packages.")

            # For logging
            i = 1
            total = len(avail_updates)

            applications = []
            for pkg in avail_updates:
                try:
                    app_name = pkg.get(PkgKeys.name, '')

                    dependencies = self._get_dependencies(
                        app_name,
                        pkg[PkgKeys.version],
                        pkg[PkgKeys.release],
                        pkg[PkgKeys.arch]
                    )

                    lookup_name = pkg.get(PkgKeys.lookup_name, '')
                    vendor_severity = \
                        severity_of_pkgs.get(lookup_name, '')

                    app = CreateApplication.create(
                        app_name,
                        pkg[PkgKeys.full_version],
                        pkg[PkgKeys.description],  # description
                        [],  # file_data
                        dependencies,  # dependencies
                        '',  # support_url
                        vendor_severity,  # vendor_severity
                        '',  # file_size
                        '',  # vendor_id,
                        '',  # vendor_name
                        None,  # install_date
                        pkg[PkgKeys.release_date],  # release_date
                        False,  # installed
                        "",  # repo
                        "no",  # reboot_required
                        "yes"  # TODO: check if app is uninstallable
                    )

                    if app:
                        logger.debug(app)
                        applications.append(app)

                    logger.debug("{0} out of {1} finished.".format(i, total))
                    i += 1

                except Exception as e:
                    logger.error(
                        "Failed to create app for: {0}".format(app_name)
                    )
                    logger.exception(e)

                    continue

            logger.debug("Done getting available updates.")

            return applications

        except Exception as e:
            logger.error("Failed to retrieve available updates.")
            logger.exception(e)

            return []

    def install_update(self, install_data, update_dir=None):
        logger.debug('Received install_update call.')

        old_install_list = self.get_installed_applications()

        success = 'false'
        error = ''
        restart = 'false'
        app_encoding = CreateApplication.null_application().to_dict()
        apps_to_delete = []
        apps_to_add = []

        success, error, restart = self._yum_update(install_data.name)

        if success == 'true':

            new_install_list = self.get_installed_applications()

            app = self._get_installed_app(install_data.name, new_install_list)
            app_encoding = app.to_dict()

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
