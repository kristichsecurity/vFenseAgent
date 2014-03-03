import os
import re
import datetime
import traceback

import logging
import logging.handlers

LogFilePath = None

LogFormat = '%(levelname)s : %(asctime)s : %(message)s'
LogDateFormat = '%m/%d/%Y %I:%M:%S %p'
LogLineRegex = r'^[A-Z]+ : (\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} (?:PM|AM)) : .+'

LoggingFormatter = None

RollingDateParseRegex = r'.+\.(\d{4}-\d{2}-\d{2})'

_logger = None
_initialized = False

class LogLevel():
    Debug = 'debug'
    Info = 'info'
    Warning = 'warning'
    Error = 'error'
    Critical = 'critical'

def log(message, log_level=LogLevel.Info):

    if _initialized:
        if log_level == 'debug':
            _logger.debug(message)

        elif log_level == 'info':
            _logger.info(message)

        elif log_level == 'warning':
            _logger.warning(message)

        elif log_level == 'error':
            _logger.error(message)

        elif log_level == 'critical':
            _logger.critical(message)


def debug(message):

    log(message, LogLevel.Debug)


def info(message):

    log(message, LogLevel.Info)


def warning(message):

    log(message, LogLevel.Warning)


def error(message):

    log(message, LogLevel.Error)


def critical(message):

    log(message, LogLevel.Critical)


def log_exception(e, log_level=LogLevel.Error):
    log("Exception: %s" % str(e), log_level)
    tb = traceback.format_exc()
    log(tb, LogLevel.Debug)


def exception(e, log_level=LogLevel.Error):

    log_exception(e, log_level=LogLevel.Error)


def _get_log_level(level):

    if level == 'info':
        return logging.INFO

    elif level == 'debug':
        return logging.DEBUG

    elif level == 'warning':
        return logging.WARNING

    elif level == 'error':
        return logging.ERROR

    elif level == 'critical':
        return logging.CRITICAL

def _get_datetime(log_line):
    """ Parses the date and time from a line in the log file. """

    log_datetime = None

    match = re.search(LogLineRegex, log_line)
    if match:
        log_datetime = datetime.datetime.strptime(match.group(1), LogDateFormat)

    return log_datetime

def get_logs_between_dates(file_path, start_datetime, end_datetime):
    log_content = []

    try:
        with open(file_path, 'r') as log_file:

            # Using as a barrier from appending lines with no datetime in
            # beginning of line when dealing with weird start/end datetimes.
            parsing = False

            for log_line in log_file.readlines():
                log_datetime = _get_datetime(log_line)

                # Means it's a new line of log
                if log_datetime:

                    pasring = True

                    if (start_datetime <= log_datetime and 
                        log_datetime <= end_datetime):

                        log_content.append(log_line)
                        continue

                    elif start_datetime > log_datetime:
                        continue

                    else:
                        break

                else:
                    if parsing:
                        log_content.append(log_line)

    except Exception as e:
        pass

    return ''.join(log_content)

def get_last_log_datetime(log_path):
    last_log_datetime = None

    try:

        with open(log_path, 'r') as current_log:

            for log_line in reversed(current_log.readlines()):
                log_datetime = _get_datetime(log_line)

                if log_datetime:
                    last_log_datetime = log_datetime

    except Exception as e:
        pass

    return last_log_datetime

def retrieve_log_paths(log_date, log_dir):
    """ 
    Retrieves the path of a log which corresponds to the given log_date.

    @param log_date: Must be of format 'yyyy-mm-dd'
    @param log_dir: Specify where the logs are stored.
    @return: Full log path if found, '' otherwise.
    """

    log_path = []

    for log in os.listdir(log_dir):
        full_path = os.path.abspath(log)

        match = re.search(RollingDateParseRegex, full_path)
        if match:
            if log_date == match.group(1):
                log_path.append(full_path)

    return log_path

def add_log_handler(filename, roll_interval='midnight', backupCount=7):
    """ 
    Adds handler to _logger with the formatting specified in LoggingFormatter.
    """

    global _logger

    handler = logging.handlers.TimedRotatingFileHandler(filename,
                                                        when=roll_interval,
                                                        backupCount=backupCount)
    handler.setFormatter(LoggingFormatter)

    _logger.addHandler(handler)

def remove_log_handler(handler):
    """ Removes handler from _logger. """

    global _logger

    handler.close()
    _logger.removeHandler(handler)

def remove_all_handlers():
    """ Removes all handlers from logger. """

    for handler in _logger.handlers:
        remove_log_handler(handler)

def initialize(log_filename, log_dir, log_level=LogLevel.Debug):
    """ Initialize logging for the agent.

    @return: Nothing
    """
    global LogFilePath
    global LoggingFormatter
    global _initialized
    global _logger

    LogFilePath = os.path.join(log_dir, log_filename + '.log')

    LoggingFormatter = logging.Formatter(fmt=LogFormat, datefmt=LogDateFormat)

    _logger = logging.getLogger("log.all")
    _logger.setLevel(_get_log_level(log_level))
    _logger.propagate = False

    add_log_handler(LogFilePath)

    _initialized = True

