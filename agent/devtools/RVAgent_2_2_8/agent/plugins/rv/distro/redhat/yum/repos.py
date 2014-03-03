import os
import xml.etree.ElementTree as ET
import glob
import gzip
import urllib
from ConfigParser import ConfigParser

from utils import logger
from utils import settings

from rv.distro.redhat import yum
from rv.distro.redhat.yum import MetaPackage, Repo


class RepoData():
    """General manager class to get needed data from all of the repos.
    """

    def __init__(self):

        self._repo_dir = '/etc/yum.repos.d'
        self._yum_vars = yum.yum_vars
        self.repos = self._load_repos()

    def _load_repos(self):
        """Loads up all of the repos in the yum repo directory.

        Returns:

            - A dict of Repos indexed by name (the yum unique id).

        """

        repo_files = glob.glob(os.path.join(self._repo_dir, '*.repo'))
        repos = {}

        for f in repo_files:

            try:

                for repo in self.parse_repo_file(f):

                    repos[repo.id] = repo

            except Exception as e:

                logger.error('Could not parse %s. Skipping.' % f)
                logger.exception(e)

        return repos

    def get_repo(self, _id):
        """Gets the named repo.

        Args:

            - _id: The unique ID of the repo.

        Returns:

            - A Repo instance. None if it doesn't exist.

        """

        return self.repos.get(_id)

    def parse_repo_file(self, filename):
        """Parse a .repo file.

        Args:

            - filename: Path to the repo file.

        Returns:

            - A list of the repos from the file.

        """

        repos = []

        try:

            self._basic_file_cleanup(filename)

        except Exception as e:
            logger.error("Could not clean up repo file: %s." % filename)
            logger.exception(e)

        try:

            defaults = {

                'enabled': '1',
                'baseurl': ''
            }

            repo_file = ConfigParser(defaults)
            repo_file.read(filename)

            for section in repo_file.sections():

                _id = self._replace_yum_vars(section)
                enabled = repo_file.getint(section, 'enabled')

                name = self._replace_yum_vars(
                    repo_file.get(section, 'name')
                )

                url = self._replace_yum_vars(
                    repo_file.get(section, 'baseurl')
                )

                # No soup for you without a baseurl.
                if (
                    url == ''
                    or enabled == 0
                ):
                    continue

                url = self._check_for_redirects(url)

                r = Repo(
                    _id,
                    name,
                    url,
                    enabled
                )

                repos.append(r)

            #with open(filename) as inf:

            #    repo_lines = [l.replace('\n', '') for l in inf]

            #    repo = None
            #    found_repo = False

            #    for i in range(len(repo_lines)):

            #        if (
            #            repo_lines[i].startswith('[') and
            #            repo_lines[i].endswith(']')
            #        ):

            #            if repo:

            #                r = Repo(
            #                    repo['id'],
            #                    repo['name'],
            #                    repo['url'],
            #                    repo['enabled']
            #                )
            #                repos.append(r)

            #            repo = {}
            #            repo['enabled'] = True

            #            repo['id'] = (
            #                repo_lines[i].replace('[', '')
            #                .replace(']', '')
            #                .strip()
            #            )

            #            found_repo = True

            #            continue

            #        if found_repo:

            #            if repo_lines[i].startswith('name='):

            #                try:

            #                    name = repo_lines[i].partition('=')[2].strip()

            #                except:

            #                    name = repo['id']

            #                repo['name'] = name

            #                continue

            #            if repo_lines[i].startswith('enabled='):

            #                enabled = repo_lines[i].partition('=')[2].strip()

            #                if enabled == 1:
            #                    repo['enabled'] = True
            #                else:
            #                    repo['enabled'] = False

            #                continue

            #            if (
            #                repo_lines[i].startswith('baseurl=') or
            #                'baseurl=' in repo_lines[i]
            #            ):

            #                repo['url'] = (
            #                    repo_lines[i].partition('=')[2].strip()
            #                )

            #                repo['url'] = repo['url'].replace(
            #                    '$basearch', self._yum_vars['basearch']
            #                )

            #                repo['url'] = repo['url'].replace(
            #                    '$releasever', self._yum_vars['releasever']
            #                )

            #                repo['url'] = repo['url'].replace(
            #                    '$arch', self._yum_vars['arch']
            #                )

            #                continue

            #            if i == len(repo_lines) - 1:

            #                r = Repo(
            #                    repo['id'],
            #                    repo['name'],
            #                    repo['url'],
            #                    repo['enabled']
            #                )
            #                repos.append(r)

        except Exception as e:

            logger.error("Could not parse repo file %s." % filename)
            logger.exception(e)

        return repos

    def _check_for_redirects(self, url):
        """Determines if the url given redirects to another one. And if it does
        then return that url.

        Args:

            - url: Url to check.

        Returns:

            The redirect url if there is one. Otherwise the original url
                is returned.

        """

        try:

            r = urllib.urlopen(url)
            new_url = r.geturl()

            if new_url != url:
                logger.debug("Redirect URL detected.")
                logger.debug("Using %s instead of %s." % (new_url, url))

                return new_url

            return url

        except Exception as e:

            logger.error("Could not verfiy url redirect.")
            logger.exception(e)

            return url

    def _replace_yum_vars(self, string):
        """Replaces the yum specific variables if present within a string.

        Args:

            - string: The str type to replace the variables.

        Returns:

            - The new string.

        """

        try:

            new_string = string.replace(
                '$releasever', self._yum_vars['releasever']
            )

            new_string = new_string.replace(
                '$basearch', self._yum_vars['basearch']
            )

            new_string = new_string.replace('$arch', self._yum_vars['arch'])

            return new_string

        except:

            return string

    def _basic_file_cleanup(self, filename):
        """Cleans up repo files according to agent needs.

        Checks:

            - If 'baseurl' is commented out (with a single '#') and
                uncomments it.
            - If 'mirrorlist' is being used and if so comments it out.

        Args:

            - filename: Complete path of the repo file to be cleaned up.

        Returns:

            Nothing
        """

        lines = []

        with open(filename) as repo_file:

            lines = [l.replace('\n', '') for l in repo_file]

        with open(filename, 'w+') as repo_file:

            repo_found = False
            for line in lines:

                if(
                    line.startswith('[')
                    and line.endswith(']')
                ):
                    repo_found = True

                if repo_found:

                    # Comments that we are interested in.
                    if line.startswith('#baseurl'):

                        repo_file.write(line.replace('#', '', 1) + '\n')
                        continue

                    # ------------------------------------------

                    if line.startswith('mirrorlist'):

                        repo_file.write('#' + line + '\n')
                        continue

                repo_file.write(line + '\n')


class PrimaryXml():
    """Wrapper class to help parse primary.xml file of yum repos.
    """

    def __init__(self, primary_file):

        primary = ET.parse(primary_file)
        self.root = primary.getroot()

    def find_packages(self, package_name):
        """Find specific packages.

        Iterates over primary.xml looking for the all packages that go
        by package_name.

        Args:

            - package_name: Name of the package to find.

        Returns:

            - A list of MetaPackages. Empty list otherwise.

        """

        metaPackages = []

        if not self.root:
            return metaPackages

        for package in self.root:
            mp = None

            try:

                if package[0].text == package_name:

                    children = package.getchildren()

                    name = children[0].text

                    version_data = children[2].attrib
                    version = version_data['ver']
                    release = version_data['rel']
                    arch = children[1].text

                    complete_version = "{0}-{1}".format(version, release)

                    nvra = "{NAME}-{VERSION}-{RELEASE}.{ARCH}".format(
                        NAME=name,
                        VERSION=version,
                        RELEASE=release,
                        ARCH=arch
                    )

                    # Everything below here is optional.
                    # Hence all of the try/excepts..

                    try:
                        checksum = children[3].text
                    except:
                        checksum = ''

                    # Skipping [4]. That's a short summary.

                    try:
                        description = children[5].text
                    except:
                        description = ''

                    # Skipping [6]. "Packager".

                    try:
                        url = children[7].text
                    except:
                        url = ''

                    try:
                        time_data = children[8].attrib
                        release_date = float(time_data['build'])
                    except:
                        release_date = float()

                    try:
                        size_data = children[9].attrib
                        size = size_data['package']
                    except:
                        size = ''

                    try:
                        format_children = children[11].getchildren()
                        vendor = format_children[1].text
                    except:
                        vendor = ''

                    try:
                        location = children[10].attrib['href']
                    except:
                        location = ''

                    mp = MetaPackage(name, version, release, complete_version,
                                     nvra, arch, description, checksum, url,
                                     release_date, size, vendor, location)

            except Exception as e:

                logger.error(
                    "Could not find package {}. Skipping.".format(package_name)
                )
                logger.exception(e)

            if mp:
                metaPackages.append(mp)

        return metaPackages


def get_primary_file(repo_id, repo_data):
    """Get a repo's primary.xml file.

    Big helper function. It downloads the primary.xml file from the repo
    because newer versions of yum download a sqlite file and we are
    *NOT* getting into that.

    Args:

        - repo_id: Unique ID of the repo.

        - repo_data: A RepoData instance used to look up repo information.

    Returns:

        - A PrimaryXml instance of the primary file. None otherwise.

    """

    primary_xml = None

    cache_dir = yum.get_cache_dir()
    repo_cache = os.path.join(cache_dir, repo_id)
    repo_md = os.path.join(repo_cache, 'repomd.xml')

    location = None

    if not os.path.exists(repo_md):

        logger.debug("%s does not exist." % repo_md)
        return None

    try:

        repo_xml = ET.parse(repo_md).getroot()

        for data in repo_xml.getchildren():

            if data.attrib:

                if 'type' in data.attrib:

                    if data.attrib['type'] == 'primary':

                        for child in data.getchildren():

                            if 'location' in child.tag:

                                location = child.attrib['href']

        if location:

            rd = repo_data
            repo = rd.get_repo(repo_id)

            primary_url = os.path.join(repo.url, location)
            filename = 'temp_primary_%s.xml.gz' % repo_id
            filepath = os.path.join(settings.TempDirectory, filename)

            urllib.urlretrieve(primary_url, filepath)

            xml = gzip.open(filepath, 'rb')

            primary_xml = PrimaryXml(xml)

            xml.close()

    except Exception as e:

        logger.error("Could not get primary.xml for repo: %s." % repo_id)
        logger.debug("Path to primary.xml: %s" % primary_url)
        logger.exception(e)

    try:
        os.remove(filepath)
    except:
        pass

    return primary_xml
