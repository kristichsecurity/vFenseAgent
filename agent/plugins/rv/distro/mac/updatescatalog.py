import os
import json
import glob

from utils import logger
from utils import settings
from utils.distro.mac.plist import PlistInterface


class UpdatesCatalog:
    def __init__(self, catalogs_dir, catalog_filename):
        self.catalogs_dir = catalogs_dir
        self.catalog_filename = catalog_filename
        self.plist = PlistInterface()

    def create_updates_catalog(self, update_apps):
        """
        Creates a catalog file which houses all the catalog information
        provided by the mac catalogs; Only for applications that need updates.
        """

        catalogs = glob.glob(os.path.join(self.catalogs_dir, '*.sucatalog'))

        try:
            key_and_app = {self.plist.get_product_key_from_app_dict(app): app
                           for app in update_apps}

            data = {}

            for catalog in catalogs:

                if len(key_and_app) == 0:
                    break

                su = self.plist.read_plist(catalog)

                for key in su.get('Products', {}).keys():

                    if len(key_and_app) == 0:
                        break

                    if key in key_and_app:
                        app_name = key_and_app[key]['name']

                        data[app_name] = su['Products'][key]

                        data[app_name]['PostDate'] = \
                            data[app_name]['PostDate'].strftime(
                                settings.DATE_FORMAT
                            )

                        reboot = self._get_reboot_required_from_data(
                            key_and_app[key]['restartRequired']
                        )
                        data[app_name]['reboot'] = reboot

                        # Stop checking for this key
                        del key_and_app[key]

            self.write_data(data)

        except Exception as e:
            logger.error("Could not create updates catalog.")
            logger.exception(e)

    def _get_reboot_required_from_data(self, reboot_string):
        reboot = 'false'

        if reboot_string == 'YES':
            reboot = 'true'

        return reboot

    def _get_file_json(self, file_path):
        with open(file_path, 'r') as _file:
            return json.load(_file)

    def get_all_data(self, ):
        """
        Returns a dictionary with all information in the updates catalog file.
        """
        return self._get_file_json(self.catalog_filename)

    def _write_file_json(self, json_data, file_path):
        with open(file_path, 'w') as _file:
            json.dump(json_data, _file, indent=4)

    def write_data(self, json_data):
        self._write_file_json(json_data, self.catalog_filename)

    def get_app_data(self, app_name):
        """
        Returns a dictionary of all the information specific to the product
        key.
        """
        return self.get_all_data().get(app_name, {})

    def get_reboot_required(self, app_name):
        reboot = 'no'

        try:
            app_data = self.get_app_data(app_name)
            reboot = app_data.get('reboot', 'no').lower()

        except Exception as e:
            logger.error(
                "Failed to get reboot required for {0}".format(app_name)
            )
            logger.exception(e)

        return reboot

    def get_release_date(self, app_name):
        """ Gets the release date of the application specified by app_name """

        release_date = ''

        try:
            app_data = self.get_app_data(app_name)
            release_date = str(app_data.get('PostDate', ''))

        except Exception as e:
            logger.error("Failed to get release date for {0}".format(app_name))
            logger.exception(e)

        return release_date

    #def get_dependencies(self, product_key):
    #    """
    #    Returns a list of dictionaries for all of the apps' dependencies with
    #    format:
    #        [
    #            {
    #              'name' : ... ,
    #              'version' : ... ,
    #              'app_id' : ...
    #            }
    #        ]
    #    """
    #
    #    dependencies = []
    #
    #    try:
    #        key_data = get_product_key_data(product_key)
    #
    #        for pkg in key_data.get('Packages', []):
    #            pass
    #
    #            dependencies.append()
    #
    #    except Exception as e:
    #        logger.error('Could not find dependencies for: {0}'.format(product_key))
    #        logger.exception(e)
    #
    #    return dependencies

    def get_file_data(self, app_name):
        """
        Returns urls and other info corresponding to the app with given
        app_name.
        """

        file_data = []

        try:
            app_data = self.get_app_data(app_name)

            for pkg in app_data.get('Packages', []):

                pkg_data = {}

                uri = pkg.get('URL', '')
                name = uri.split('/')[-1]

                pkg_data['file_name'] = name
                pkg_data['file_uri'] = uri
                pkg_data['file_size'] = pkg.get('Size', '')
                pkg_data['file_hash'] = ''

                file_data.append(pkg_data)

        except Exception as e:

            logger.error('Could not get file_data/release date.')
            logger.exception(e)

        return file_data
