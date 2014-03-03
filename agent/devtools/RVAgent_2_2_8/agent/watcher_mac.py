import subprocess
import sys
import os
import time
from collections import namedtuple

sys.path.append(os.path.join(os.getcwd(), "src"))

from utils import settings
from utils import logger

settings.initialize('watcher')

original_plist = '/opt/TopPatch/agent/daemon/com.toppatch.agent.plist'
osx_plist = '/System/Library/LaunchDaemons/com.toppatch.agent.plist'
daemon_label = 'com.toppatch.agent'
cp_command = ['/bin/cp', original_plist, osx_plist]
list_command = ['/bin/launchctl', 'list']
load_command = ['/bin/launchctl', 'load', '-w', osx_plist]
unload_command = ['/bin/launchctl', 'unload', '-w', osx_plist]
start_command = ['/bin/launchctl', 'start', daemon_label]
stop_command = ['/bin/launchctl', 'stop', daemon_label]

check_in_seconds = 60

def start_agent():

    result = False
    try:

        process = subprocess.Popen(start_command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        raw_output, error_output = process.communicate()

        if raw_output == '' and error_output == '':

            logger.log('Agent started.')
            result = True

        elif 'No such process' in error_output:

            logger.log('Agent not found.')

        else:

            logger.log('Unknown output: "%s"' % error_output)

    except Exception as e:

        logger.log("Could not start agent.", logger.LogLevel.Error)
        logger.log_exception(e)

    return result


def restart_agent():

    try:

        process = subprocess.Popen(stop_command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        raw_output, error_output = process.communicate()

        if raw_output == '' and error_output == '':

            logger.log('Agent has restarted.')

        elif 'No such process' in error_output:

            logger.log('Agent not found. Nothing to restart.')

        else:

            logger.log('Unknown output: "%s"' % error_output)

    except Exception as e:

        logger.log("Could not start agent.", logger.LogLevel.Error)
        logger.log_exception(e)


def load_agent():

    try:

        process = subprocess.Popen(load_command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        raw_output, error_output = process.communicate()

        if raw_output == '' and error_output == '':

            logger.log('Agent loaded.')

        elif 'Already loaded' in error_output:

            logger.log('Agent is already loaded.')

        else:

            logger.log('Unknown output: "%s"' % error_output)

    except Exception as e:

        logger.log("Could not load agent.", logger.LogLevel.Error)
        logger.log_exception(e)


def unload_agent():

    try:

        process = subprocess.Popen(unload_command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        raw_output, error_output = process.communicate()

        if raw_output == '' and error_output == '':

            logger.log('Agent unloaded.')

        elif 'Error unloading' in error_output:

            logger.log('Agent is not loaded/installed.')

        else:

            logger.log('Unknown output: "%s"' % error_output)

    except Exception as e:

        logger.log("Could not load agent.", logger.LogLevel.Error)
        logger.log_exception(e)

AgentStatus = namedtuple('AgentStats', ['loaded', 'running'])


def agent_running_stats():

    ps_info = []

    running = False
    loaded = False

    process = subprocess.Popen(list_command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    raw_output, error_output = process.communicate()

    for line in raw_output.splitlines():
        pid, run, pname = line.split('\t')
        ps_info.append((pname, run, pid))

    for p in ps_info:

        if daemon_label == p[0]:
            # p[1] can either be:
            #  : '0' meaning not running.
            #  : '-' meaning its running.
            loaded = True

            if p[1] == '-':

                running = True

                break

            elif p[1] == '0':

                running = False

    status = AgentStatus(loaded, running)
    logger.log(str(status), logger.LogLevel.Debug)

    return status


if __name__ == '__main__':

    logger.log("Starting watcher daemon.")

    while True:

        time.sleep(check_in_seconds)

        agent_status = agent_running_stats()

        if agent_status.loaded:

            if agent_status.running:

                logger.log("Agent is running.", logger.LogLevel.Debug)
                continue

            else:

                if not start_agent():

                    load_agent()

        else:

            load_agent()





