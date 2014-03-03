import os
import sqlite3

from utils import settings
from utils import logger
from application import Application


class SqliteRv():
    """ Helps with managing the sqlite file used by rv.
    Only one instance of this class should exist.
    """

    def __init__(self):
        self._application_table = 'applications'
        # self._connection = sqlite3.connect(
        #     os.path.join(settings.DbDirectory, 'rv.adb'),
        #     check_same_thread=False)

        #self._connection.text_factory = str
        # this way all fetch*() will return dict instead of tuple.
        self._connection.row_factory = sqlite3.Row

        self.recreate_application_table()

    def _create_application_table(self):

        with self._connection:

            # Order of columns is crucial here.
            all_cols = (self._application_table,
                        ApplicationColumn.Id,
                        ApplicationColumn.VendorId,
                        ApplicationColumn.VendorName,
                        ApplicationColumn.Name,
                        ApplicationColumn.Description,
                        ApplicationColumn.Version,
                        ApplicationColumn.Urls,
                        ApplicationColumn.FileSize,
                        ApplicationColumn.SupportURL,
                        ApplicationColumn.VendorSeverity,
                        ApplicationColumn.TopPatchSeverity,
                        ApplicationColumn.InstallDate,
                        ApplicationColumn.ReleaseDate,
                        ApplicationColumn.Installed)

            cursor = self._connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS %s "
                           "(%s INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,"
                           "%s TEXT NOT NULL UNIQUE,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s BOOL NULL)" % all_cols)

    def add_application(self, application):
        result = False

        if self.application_exist(application):
            logger.debug(
                "Application %s already exist. Ignoring." % application.vendor_id
            )
            return result

        with self._connection:

            cursor = self._connection.cursor()

            # Order is crucial here!
            values = (application.vendor_id,
                      application.vendor_name,
                      application.name,
                      application.description,
                      application.version,
                      self._urls_to_string(application.urls),
                      application.file_size,
                      application.support_url,
                      application.vendor_severity,
                      application.toppatch_severity,
                      application.install_date,
                      application.release_date,
                      application.installed
            )

            cursor.execute("INSERT INTO %s (%s) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" %
                           (self._application_table,
                            ApplicationColumn.AllColumns), values)

            logger.debug("Added application ID# %s." % application.vendor_id)

            result = True
            return result

    def application_exist(self, application):

        with self._connection:
            cursor = self._connection.cursor()

            select_sql = "SELECT * FROM %s WHERE %s='%s' LIMIT 1" % (
                self._application_table,
                ApplicationColumn.VendorId,
                application.vendor_id
            )

            cursor.execute(select_sql)

            result = cursor.fetchone()

            if result is None:
                return False
            else:
                return True

    def get_available_updates(self):
        return self.get_applications(False)

    def get_installed_applications(self):
        return self.get_applications(True)

    def get_updates_and_applications(self):
        return self.get_applications()

    def get_application(self, vendor_id):
        """ Returns an Application instance based on the 'vendor_id'.
        @param vendor_id: Vendor ID of the application.
        @return: An Application instance.
        """

        try:

            with self._connection:
                cursor = self._connection.cursor()

                select_sql = "SELECT * FROM %s WHERE %s='%s'" % (
                    self._application_table, ApplicationColumn.VendorId,
                    vendor_id)

                cursor.execute(select_sql)

                row = cursor.fetchone()

                app = self._get_application_from_row(row)

        except Exception as e:
            logger.error("Could not get application id %s." % vendor_id)
            logger.exception(e)
            app = None

        return app

    def get_applications(self, installed=None):
        """ Returns applications based on the 'installed' parameter.
        If it's None then all applications are returned. If True, only
        applications installed are returned. If False, then only applications
        not installed (ie: are updates) are returned.

        @param installed: Parameter used to filter applications with.
        @return: List of applications objects.
        """

        application_list = []

        with self._connection:
            cursor = self._connection.cursor()

            # Checking for 'None' to show explicit sql statements for
            # each scenario.
            if installed is None:
                select_sql = "SELECT * FROM %s" % self._application_table

            elif installed is True:
                select_sql = "SELECT * FROM %s WHERE %s = 1" % (
                    self._application_table, ApplicationColumn.Installed
                )

            elif installed is False:
                select_sql = "SELECT * FROM %s WHERE %s = 0" % (
                    self._application_table, ApplicationColumn.Installed
                )

            cursor.execute(select_sql)

            rows = cursor.fetchall()

            for row in rows:
                update = self._get_application_from_row(row)
                application_list.append(update)

        return application_list

    def _get_application_from_row(self, row):

        if not row:
            return None

        application = Application()

        application.vendor_id = row[ApplicationColumn.VendorId]
        application.vendor_name = row[ApplicationColumn.VendorName]
        application.name = row[ApplicationColumn.Name]
        application.description = row[ApplicationColumn.Description]
        application.version = row[ApplicationColumn.Version]
        application.urls = self._string_to_urls(row[ApplicationColumn.Urls])
        application.file_size = row[ApplicationColumn.FileSize]
        application.support_url = row[ApplicationColumn.SupportURL]

        application.vendor_severity = row[ApplicationColumn.VendorSeverity]
        application.toppatch_severity = row[ApplicationColumn.TopPatchSeverity]

        application.install_date = row[ApplicationColumn.InstallDate]
        application.release_date = row[ApplicationColumn.ReleaseDate]

        application.installed = bool(row[ApplicationColumn.Installed])

        return application

    def _urls_to_string(self, urls):
        return ','.join([url for url in urls])

    def _string_to_urls(self, url_string):
        if url_string == "":
            return []
        else:
            return url_string.split(',')

    def drop_table(self, table_name):
        """ Drop a specific table from the Rv database.
        @param table_name: Table to drop
        @return:
        """

        connection = self._connection

        with connection:
            cursor = connection.cursor()
            cursor.execute("DROP TABLE IF EXISTS %s" % table_name)

    def recreate_application_table(self):
        """ Recreates the application table but not the data.
        @return: Nothing
        """

        self.drop_table(self._application_table)
        self._create_application_table()


class ApplicationColumn():
    """ Keeps all columns belonging to the applications table in one place.
    If order of columns is ever an issue, then use the order in which each
    property is defined.
    """

    Id = "id"
    VendorId = "vendor_id"
    VendorName = "vendor_name"
    Name = "name"
    Description = "description"
    Version = "version"
    Urls = "urls"
    FileSize = "file_size"
    SupportURL = "support_url"
    VendorSeverity = "vendor_severity"
    TopPatchSeverity = "toppatch_severity"
    InstallDate = "install_date"
    ReleaseDate = "release_date"
    Installed = "installed"

    AllColumns = "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s " % (
        VendorId, VendorName, Name, Description, Version, Urls,
        FileSize, SupportURL, VendorSeverity, TopPatchSeverity, InstallDate,
        ReleaseDate, Installed
    )
