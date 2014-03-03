import sqlite3

from utils import settings
from utils import logger


class SqliteManager():
    """ Helps with managing the sqlite file used by the agent.
    Only one instance of this class should exist.
    """

    def __init__(self):
        self._operations_table = 'operations'
        self._settings_table = 'settings'
        self._connection = sqlite3.connect(settings.AgentDb,
                                           check_same_thread=False)

        #self._connection.text_factory = str
        # this way all fetch*() will return dict instead of tuple.
        self._connection.row_factory = sqlite3.Row

        self._create_operation_table()

    def _create_operation_table(self):
        with self._connection:

            # Order of columns is crucial here.
            all_cols = (self._operations_table,
                        OperationColumn.Id,
                        OperationColumn.OperationType,
                        OperationColumn.OperationId,
                        OperationColumn.RawOperation,
                        OperationColumn.RawResult,
                        OperationColumn.DateTimeReceived,
                        OperationColumn.DateTimeSent,
                        OperationColumn.ResultsSent)

            cursor = self._connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS %s "
                           "(%s INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL,"
                           "%s BOOL NULL)" % all_cols)

    def _create_settings_table(self):
        with self._connection:

            # Order of columns is crucial here.
            all_cols = (self._settings_table,
                        SettingColumn.Id,
                        SettingColumn.Username,
                        SettingColumn.Password)

            cursor = self._connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS %s "
                           "(%s INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,"
                           "%s TEXT NULL,"
                           "%s TEXT NULL)" % all_cols)

    def add_operation(self, operation, received_time):

        try:

            with self._connection:

                cursor = self._connection.cursor()

                values = (operation.type,
                          operation.id,
                          operation.raw_operation.replace(r"'", r"''"), # Escape single quote
                          settings.EmptyValue,  # raw message value
                          received_time,
                          settings.EmptyValue,  # date time sent
                          False)

                logger.debug("Adding operation %s." % operation.id)
                cursor.execute("INSERT INTO %s (%s) "
                               "VALUES (?, ?, ?, ?, ?, ?, ?)" %
                               (self._operations_table,
                                OperationColumn.AllColumns), values)

        except Exception as e:

            logger.error("Could not add operation %s." % operation.id)
            logger.exception(e)

    def edit_operation(self, operation, result_sent=False, sent_time=None):

        if sent_time is None:
            sent_time = settings.EmptyValue

        try:
            with self._connection:

                cursor = self._connection.cursor()

                # Escape any single-quotes. Sqlite use two single quotes.
                values = ",".join([
                    "%s = '%s'" % (OperationColumn.OperationType,
                                   operation.type),
                    "%s = '%s'" % (OperationColumn.OperationId, operation.id),
                    "%s = '%s'" % (OperationColumn.RawOperation,
                                   operation.raw_operation.replace(r"'", r"''")),
                    "%s = '%s'" % (OperationColumn.RawResult,
                                   operation.raw_result.replace(r"'", r"''")),
                    "%s = '%s'" % (OperationColumn.DateTimeSent, sent_time),
                    "%s =  %s" % (OperationColumn.ResultsSent, int(result_sent))
                ])

                logger.debug("Editing operation %s." % operation.id)
                cursor.execute("UPDATE %s SET %s WHERE %s = '%s'" % (
                    self._operations_table, values, OperationColumn.OperationId,
                    operation.id))

        except Exception as e:

            logger.error("Could not edit operation %s." % operation.id)
            logger.exception(e)

    def add_result(self, result_op, result_sent=False, sent_time=None):

        if sent_time is None:
            sent_time = settings.EmptyValue

        try:

            with self._connection:

                cursor = self._connection.cursor()

                values = (result_op.type,
                          result_op.id,
                          settings.EmptyValue, # Escape single quote
                          result_op.raw_result,  # raw message value
                          settings.EmptyValue,
                          sent_time,  # date time sent
                          result_sent)

                logger.debug("Adding result_op %s." % result_op.id)
                cursor.execute("INSERT INTO %s (%s) "
                               "VALUES (?, ?, ?, ?, ?, ?, ?)" %
                               (self._operations_table,
                                OperationColumn.AllColumns), values)

        except Exception as e:

            logger.error("Could not add result_op %s." % result_op.id)
            logger.exception(e)


class OperationColumn():
    """ Keeps all columns belonging to the operations table in one place.
    If order of columns is ever an issue, then use the order in which each
    property is defined.
    """

    Id = "id"
    OperationType = "operation_type"
    OperationId = "operation_id"
    RawOperation = "raw_operation"
    RawResult = "raw_result"
    DateTimeReceived = "datetime_received"
    DateTimeSent = "datetime_sent"
    ResultsSent = "results_sent"

    AllColumns = "%s, %s, %s, %s, %s, %s, %s " % (OperationType, OperationId,
        RawOperation, RawResult, DateTimeReceived, DateTimeSent, ResultsSent)

class SettingColumn():
    """ Keeps all columns belonging to the settings table in one place.
    If order of columns is ever an issue, then use the order in which each
    property is defined.
    """

    Id = "id"
    Username = "un"
    Password = "pw"

    AllColumns = "%s, %s " % (Username, Password)
