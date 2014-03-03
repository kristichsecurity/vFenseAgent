import os
import plistlib
import subprocess

from utils import logger


class PlistInterface:
    def __init__(self):
        pass

    def read_plist(self, plist_path):

        """
        Reads data from a plist file. Keys in the plist files are used for the
        dict keys.

        @param plist_path: Full path to the plist file
        @return: a python dict. None if error is encountered.
        """

        try:
            plist = plistlib.readPlist(plist_path)

            return plist
        except Exception as e:
            logger.error("Failed to read plist: {0}".format(plist_path))
            logger.exception(e)

        return {}

    def get_plist_app_dicts(self, plist_path):
        """
        Returns a list metadata of applications retrieved from the plist.
        """

        try:
            data = self.read_plist(plist_path)
            return data.get('phaseResultsArray', [])
        except Exception as e:
            logger.error("Failed getting update apps from plist.")
            logger.exception(e)

        return {}

    def get_plist_app_dicts_from_string(self, string):
        """
        Returns a list of metadata of applications retrieved from the string.
        """
        data = self.read_plist_string(string)
        return data.get('phaseResultsArray', [])

    def get_app_dict_from_plist(self, plist_path, app_name):
        """
        Returns dictionary with data corresponding to the app_name given.
        """
        try:
            app_dicts = self.get_plist_app_dicts(plist_path)

            for app_dict in app_dicts:
                if app_dict.get('name', '') == app_name:
                    return app_dict

        except Exception as e:
            logger.error("Failed getting info from plist for: " + app_name)
            logger.exception(e)

        return {}

    def get_product_key_from_app_dict(self, app_dict):
        return app_dict.get('productKey', '')

    def get_product_key(self, plist, app_name):
        app_data = self.get_app_dict_from_plist(plist, app_name)

        return self.get_product_key_from_app_dict(app_data)

    def read_plist_string(self, string):

        """
        Reads data from a string. Keys in the plist files are used for the
        dict keys.

        @param string: A plist-format str type.
        @return: a python dict. None if error is encountered.
        """

        try:
            plist = plistlib.readPlistFromString(string)

            return plist

        except Exception as e:
            logger.error("Failed to read plist from string.")
            logger.exception(e)

        return {}

    def convert_plist(self, plist_path, new_file_path, frmt='xml1'):

        """
        Converts a plist file to another supported plist-format (XML, binay, or
        json). Uses the OS X utility 'plutil'.

        @param plist_path: Full path to the plist file
        @param new_file_path: Full path to the new converted plist file
        @param frmt: Format to convert to
        @return: Nothing
        """

        try:
            cmd = ['plutil', '-convert', frmt, '-o', new_file_path, plist_path]
            subprocess.call(cmd, shell=False)

        except Exception as e:
            logger.error("Could not convert plist.")
            logger.exception(e)

    def convert_and_read_plist(self, plist_path, new_file_path=None,
                               frmt='xml1', save=False):

        """
        Converts a plist file to another supported plist-format: xml1
        (default), binay1, or json.  Uses the OS X utility 'plutil'.

        @param plist_path: Full path to the plist file
        @param new_file_path: Full path to the new converted plist file
        @param save: Boolean value whether or not to save the file.
        @return: a python dict of the converted plist
        """

        if new_file_path is None:
            new_file_path = '/var/tmp/temp_plist.plist'

        self.convert_plist(plist_path, new_file_path, frmt)

        plist = self.read_plist(new_file_path)

        if not save:
            os.remove(new_file_path)

        return plist
