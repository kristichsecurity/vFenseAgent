import sqlite3

from data.update import Update
from utils import logger


_db_file_path = '/opt/TopPatch/agent/db/agentdb.tpdb'
_connection = None
_packages_table = 'packages'

PackageTable = _packages_table


def initialize():

    global _connection # f'ing ugly global
    _connection = sqlite3.connect(_db_file_path, check_same_thread=False)
    _connection.text_factory = str

    # this way fetch*() will return dict instead of tuple.
    _connection.row_factory = sqlite3.Row

    _create_packages_table()

def _create_packages_table():

    with _connection:

        cursor = _connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS %s" % _packages_table)
        cursor.execute(""" CREATE TABLE IF NOT EXISTS %s (id INTEGER PRIMARY KEY,
                           name TEXT,
                           version_release TEXT,
                           description TEXT,
                           support_url TEXT,
                           severity TEXT,
                           toppatch_id TEXT UNIQUE,
                           vendor_id TEXT,
                           date_installed TEXT,
                           date_published TEXT,
                           is_update BOOL,
                           package_url) """ % _packages_table)


def does_table_exist(table):

    with _connection:

        cursor = _connection.cursor()
        cursor.execute('SELECT name FROM sqlite_master WHERE name="%s"' % table)

        row = cursor.fetchone()

        if row is None:
            return False

        return True


def get_db_connection():
    """
    A connection instance to use with the sqlite database. DO NOT CLOSE IT!!
    @return: Sqlite connection.
    """
    return _connection


def save_package_list(package_list):

    for package in package_list:
        save_package(package)


def save_package(package):

    with _connection:

        cursor = _connection.cursor()

        values = (package.name,
                  package.version_release,
                  package.description,
                  package.support_url,
                  package.severity,
                  package.toppatch_id,
                  package.vendor_id,
                  package.date_installed,
                  package.date_published,
                  package.is_update,
                  package.package_url)

        logger.debug("Adding TPID# %s" % package.toppatch_id)
        cursor.execute("INSERT INTO %s (name, version_release, description,"
                       "support_url, severity, toppatch_id, vendor_id,"
                       "date_installed, date_published, is_update, package_url)"
                       " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" %
                       _packages_table,
                       values)


def is_toppatch_id_unique(id):

    with _connection:
        cursor = _connection.cursor()
        select_sql = "SELECT * FROM %s WHERE toppatch_id='%s' LIMIT 1" \
                     % (_packages_table, id)

        cursor.execute(select_sql)

        result = cursor.fetchone()

        if result is None:
            return True
        else:
            return False


def get_package_by_id(id):

    with _connection:
        cursor = _connection.cursor()
        select_sql = "SELECT * FROM %s WHERE toppatch_id='%s' LIMIT 1" \
                     % (_packages_table, id)

        cursor.execute(select_sql)

        row = cursor.fetchone()
        if row is not None:
            update = _get_package_from_row(row)
        else:
            update = None

        return update


def get_package_by_name(name):
    with _connection:
        cursor = _connection.cursor()
        select_sql = "SELECT * FROM %s WHERE name='%s' LIMIT 1" \
                     % (_packages_table, name)

        cursor.execute(select_sql)

        row = cursor.fetchone()
        if row is not None:
            update = _get_package_from_row(row)
        else:
            update = None

        return update


def _get_package_from_row(row):

    update = Update()

    update.name = row['name']
    update.version_release = row['version_release']
    update.description = row['description']
    update.support_url = row['support_url']
    update.severity = row['severity']

    update.toppatch_id = row['toppatch_id']
    update.vendor_id = row['vendor_id']

    update.date_installed = row['date_installed']
    update.date_published = row['date_published']

    update.is_update = row['is_update']
    update.package_url = row['package_url']

    return update


def get_updates_pending():

    with _connection:
        cursor = _connection.cursor()

        select_sql = "SELECT * FROM %s WHERE is_update = 1" % _packages_table

        cursor.execute(select_sql)

        rows = cursor.fetchall()

        update_list = []

        for row in rows:
            update = _get_package_from_row(row)
            update_list.append(update)

        return update_list


def get_installed_packages():

    with _connection:
        cursor = _connection.cursor()

        select_sql = "SELECT * FROM %s WHERE is_update = 0" % _packages_table

        cursor.execute(select_sql)
        rows = cursor.fetchall()

        update_list = []

        for row in rows:
            update = _get_package_from_row(row)
            update_list.append(update)

        return update_list


def recreate_table_packages():

#    with _connection:
#        cursor = _connection.cursor()
#
#        select_sql = "DROP TABLE IF EXISTS %s" % _packages_table
#        cursor.execute(select_sql)

    _create_packages_table()
