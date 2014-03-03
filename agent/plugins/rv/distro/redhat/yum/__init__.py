import sys
import os
import subprocess
import ast
from collections import namedtuple
from ConfigParser import ConfigParser

from utils import logger

YumUpdate = namedtuple('YumUpdate', ['name', 'version', 'release',
                                     'arch', 'repo'])

MetaPackage = namedtuple('MetaPackage', ['name', 'version', 'release',
                                         'complete_version', 'nvra',
                                         'arch', 'description', 'hash', 'url',
                                         'release_date', 'size', 'vendor',
                                         'location'])

Repo = namedtuple('Repo', ['id', 'name', 'url', 'enabled'])

yum_cmd = '/usr/bin/yum'

_etc_yum = ConfigParser()
_etc_yum.read('/etc/yum.conf')
_etc_main_section = 'main'

"""Various helper functions while running yum from a separate process.
"""


def _yum_vars():
    """Gets the yum variables used for normal operation.

    Such as:

        - $basearch
        - $arch
        - $releasever

    These variables are crucial for normal yum operation. With out them,
    forget about it!

    Returns:

        - A dict with the following keys:

            - releasever
            - basearch
            - arch

    """

     # Crucial variables to get
    var_command = [
        '/usr/bin/python', '-c',
        'import yum; yb = yum.YumBase(); print yb.conf.yumvar']

    try:

        process = subprocess.Popen(var_command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        output, stderr = process.communicate()

        return ast.literal_eval(output.splitlines()[1])

    except Exception as e:

        logger.critical(
            "Could not find yum vars. ($basearch, $releasever, etc)"
        )
        logger.critical("Exiting agent now. Please contact support.")
        logger.exception(e)

        sys.exit(-1)

yum_vars = _yum_vars()


def get_cache_dir():
    """Gets yum's cache directory.

    Cache directory is used for repo metadata.

    Returns:

        - Cache directory full path. None otherwise.

    """

    try:

        if yum_vars:

            _dir = _etc_yum.get(_etc_main_section, 'cachedir').replace(
                '$basearch', yum_vars['basearch'])
            _dir = _dir.replace('$releasever', yum_vars['releasever'])

            return _dir

        raise Exception("Oops. 'yum'vars' not found.")

    except Exception as e:

        logger.error("Could not find yum's cache directory.")
        logger.exception(e)

        return None


def renew_repo_cache():
    """Renews the all enabled repo caches.

    To make sure repos info is up to date with package information.

    Returns:

        - Nothing
    """

    # Hide yum output from stdout.
    with open(os.devnull, 'w') as dev_null:

        # Clear current cache first.
        cmd = [yum_cmd, 'clean', 'all']
        exit_code = subprocess.call(cmd, stdout=dev_null, stderr=dev_null)

        # Then re-download data.
        cmd = [yum_cmd, 'makecache']
        exit_code = subprocess.call(cmd, stdout=dev_null, stderr=dev_null)

    return exit_code


def _parse_packages_from_deps(deps_info):
    """
    Yum install output consists of 6 elements for each package
        Ex:
        - 'firefox i386 24.2.0-1.0.1.el5.centos updates 50 M'
        - 'nspr i386 4.10.2-2.el5_10 updates 123 k'
    """
    packages = []
    for i in range(len(deps_info)):
        if deps_info[i] in ['b', 'k', 'M', 'G']:
            packages.append(deps_info[i-5:i+1])

    return packages


def _parse_deps_from_output(output):
    try:
        lines = output.splitlines()

        # Parsing the data by sections in order to split the data and assinging
        # 6 element chunks to one package. 6 elements is what SHOULD be
        # displayed every line but redhat uses multiple lines when names or
        # anything else get too big. Therefore it is harder to parse line by
        # line.

        # Marks the beginning of the info section for dependencies
        deps_info_section_index = None
        if 'Updating:' in lines:
            deps_info_section_index = lines.index('Updating:') + 1
        elif 'Installing:' in lines:
            deps_info_section_index = lines.index('Installing:') + 1
        else:
            raise Exception(
                "Could not find the beginning of dependencies info section."
            )

        # Marks the ending of upd_inst_dep_section_index
        ending = None
        if 'Transaction Summary' in lines:
            ending = lines.index('Transaction Summary')
        else:
            raise Exception(
                "Could not find the end of dependencies info section."
            )

        deps_section_lines = lines[deps_info_section_index:ending]

        if 'Updating for dependencies:' in deps_section_lines:
            deps_section_lines.remove('Updating for dependencies:')
        if 'Installing for dependencies:' in deps_section_lines:
            deps_section_lines.remove('Installing for dependencies:')

        return _parse_packages_from_deps(' '.join(deps_section_lines).split())

    except Exception as e:
        logger.error("Failed to parse out packages.")
        logger.exception(e)

        return []


def get_needed_dependencies(package):
    """Gets the dependencies of package.

    Gets all dependencies that the current system needs to satisfy the
    package.

    Args:

        - package: A YumUpdate instance of package to check.

    Returns:

        - A list containing YumUpdates. Empty list if no dependencies needed
            and None if unable to find dependencies.

    """

    deps = []

    try:

        #pkg = "{0}-{1}-{2}.{3}".format(
        #    package.name,
        #    package.version,
        #    package.release,
        #    package.arch
        #)

        # TODO(urgent): fix this issue with architecture and redhat,
        # too many duplicate packages with different architectures
        pkg = "{0}-{1}-{2}".format(
            package.name,
            package.version,
            package.release
        )

        cmd = [yum_cmd, 'update', pkg]

        process = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        output, _stderr = process.communicate(input='N')
        dep_packages = _parse_deps_from_output(output)

        for update_info in dep_packages:
            name = update_info[0]
            arch = update_info[1]
            repo = update_info[3]

            version_release = update_info[2].partition(':')

            if version_release[1] == ':':

                version_release = version_release[2].split('-', 1)

            else:

                version_release = version_release[0].split('-', 1)

            version = version_release[0]
            release = version_release[1]

            dep = YumUpdate(name, version, release, arch, repo)

            if(
                package.name == name
                and package.version == version
                and package.release == release
                # TODO: also avoiding arch here, check what to do with arch
                #and package.arch == arch
            ):
                continue

            deps.append(dep)

#        deps_started = False
#        for line in output.splitlines():
#
#            if (
#                line == 'Updating:'
#                or line == 'Installing:'
#            ):
#                deps_started = True
#                continue
#
#            if (
#                line == 'Updating for dependencies:'
#                or line == 'Installing for dependencies:'
#            ):
#                continue
#
#            if deps_started:
#
#                if line == '':
#                    break
#
#                update_info = line.split()
#
#                name = update_info[0]
#                arch = update_info[1]
#                repo = update_info[3]
#
#                version_release = update_info[2].partition(':')
#
#                if version_release[1] == ':':
#
#                    version_release = version_release[2].split('-', 1)
#
#                else:
#
#                    version_release = version_release[0].split('-', 1)
#
#                version = version_release[0]
#                release = version_release[1]
#
#                dep = YumUpdate(name, version, release,
#                                arch, repo)
#
#                if(
#                    package.name == name
#                    and package.version == version
#                    and package.release == release
#                    # TODO(urgent): also avoiding arch here
#                    #and package.arch == arch
#                ):
#                    continue
#
#                deps.append(dep)

    except Exception as e:

        logger.error("Could not get dependencies for %s." % package.name)
        logger.exception(e)
        deps = None

    return deps


def list_updates():
    """List packages available for update.

    Calls 'yum list updates' and parses the output.

    Returns:

        - A list containing YumUpdate instances.

    """

    # Tested with yum version 3.2.29
    cmd = [yum_cmd, 'list', 'updates']

    start_parsing = False
    start_keyword = 'Updated Packages'

    updates = []

    try:

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        output, stderr = process.communicate()

        for line in output.splitlines():

            try:

                if line == start_keyword:

                    start_parsing = True
                    continue

                if start_parsing:

                    update_data = [l for l in line.split(" ") if l != ""]

                    info = update_data[0].rpartition('.')
                    name = info[0]
                    arch = info[2]

                    version_release = update_data[1].partition(':')
                    # If ':' is present, then version string contains epoch.
                    if version_release[1] == ':':

                        version_info = version_release[2].split('-', 1)

                    else:

                        version_info = version_release[0].split('-', 1)

                    version = version_info[0]
                    release = version_info[1]

                    repo = update_data[2]

                    u = YumUpdate(name, version, release, arch, repo)

                    updates.append(u)

            except Exception as e:

                logger.error("Could not parse update. Skipping.")
                logger.exception(e)

    except Exception as e:

        logger.error("Could not check for updates.")
        logger.exception(e)

    return updates
