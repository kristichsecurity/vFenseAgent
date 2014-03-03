import sqlite3
import os

from utils import settings
from utils import logger


class SqliteMac():

    def __init__(self):
        self._table = 'update_data'
        self._connection = sqlite3.connect(
            os.path.join(settings.DbDirectory, 'mac.adb'),
            check_same_thread=False)

        self._create_update_data_table()

    def _create_update_data_table(self):

        with self._connection:

            # Order of columns is crucial here.
            all_cols = (self._table,
                        UpdateDataColumn.Id,
                        UpdateDataColumn.Name,
                        UpdateDataColumn.NeedsRestart)

            cursor = self._connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS %s "
                           "(%s INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,"
                           "%s TEXT NOT NULL UNIQUE,"
                           "%s BOOL NULL)" % all_cols)

    def recreate_update_data_table(self):
        """
        Drops and then recreates the "update_data".
        @return: Nothing
        """
        connection = self._connection

        with connection:
            cursor = connection.cursor()
            cursor.execute("DROP TABLE IF EXISTS %s" % self._table)

        self._create_update_data_table()

    def add_update_data(self, name, needs_restart=False):
        """
        Adds a new install item to the database.

        @param name: The vendor id this item refers to.
        @param needs_restart: True if restart required. False otherwise.
        @return: Nothing
        """

        if self.update_exist(name):
            logger.debug("Update %s already exist. Ignoring." % name)
            return

        _connection = self._connection
        with _connection:

            cursor = _connection.cursor()

            values = (name,
                      needs_restart)

            cursor.execute("INSERT INTO %s (%s) "
                           "VALUES (?, ?)" %
                           (self._table,
                            UpdateDataColumn.AllColumns), values)

    def edit_update_data(self, name, needs_restart=False):

        try:
            with self._connection:

                cursor = self._connection.cursor()

                values = ",".join([
                    "%s = '%s'" % (UpdateDataColumn.Name, name),
                    "%s = '%s'" % (UpdateDataColumn.NeedsRestart, needs_restart)
                ])

                logger.debug("Editing update %s." % name)

                cursor.execute("UPDATE %s SET %s WHERE %s = '%s'" % (
                    self._table, values, UpdateDataColumn.Name, name))

        except Exception as e:

            logger.info("Could not edit update %s." % name)
            logger.exception(e)

    def get_update_data(self, name):
        """
        Returns a dict with the update data.
        @param vendor_id: Used for searching the table
        @return: Dict with keys:

                    'name', 'needs_restart'
        """

        _connection = self._connection
        with _connection:
            cursor = _connection.cursor()

            select_sql = "SELECT * FROM %s WHERE %s = '%s' LIMIT 1" % (
                self._table, UpdateDataColumn.Name, name)

            cursor.execute(select_sql)
            data = cursor.fetchone()

            install_dict = {}

            # 'data' returns a tuple in 'table' order.
            # Refer to 'UpdateDataColumn' for order index.
            if data:

                install_dict[UpdateDataColumn.Name] = data[1]

                install_dict[UpdateDataColumn.NeedsRestart] = data[2]

            return install_dict

    def update_exist(self, vendor_id):

        with self._connection:
            cursor = self._connection.cursor()

            select_sql = "SELECT * FROM %s WHERE %s='%s' LIMIT 1" % (
                self._table,
                UpdateDataColumn.Name,
                vendor_id
            )

            cursor.execute(select_sql)

            result = cursor.fetchone()

            if result is None:
                return False
            else:
                return True


class UpdateDataColumn():
    """ Keeps all columns belonging to the applications table in one place.
    If order of columns is ever an issue, then use the order in which each
    property is defined.
    """

    Id = "id"
    Name = 'name'
    NeedsRestart = 'needs_restart'


    AllColumns = "%s, %s" % (
        Name, NeedsRestart
    )
