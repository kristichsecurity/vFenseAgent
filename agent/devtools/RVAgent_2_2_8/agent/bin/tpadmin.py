import os
import sys
import platform
import subprocess
import argparse


_system = platform.system().lower()

_mac_plist_path = '/System/Library/LaunchDaemons/com.toppatch.agent.plist'


def _process_cmd(cmd):

    try:

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        output, error = process.communicate()

        return output, error

    except Exception as e:

        print 'Unable to run command: %s' % cmd
        print e

        return None, None

def start_agent():

    output = None
    error = None

    if _system == 'darwin':

        cmd = [
            'launchctl', 'load', '-w',
            _mac_plist_path
        ]

        output, error = _process_cmd(cmd)

    if output:
        print output

    if error:
        print error


def stop_agent():

    output = None
    error = None

    if _system == 'darwin':

        cmd = [
            'launchctl', 'unload',
            _mac_plist_path
        ]

        output, error = _process_cmd(cmd)

    if output:
        print output

    if error:
        print error


def restart_agent():

    output = None
    error = None

    if _system == 'darwin':

        cmd = ['launchctl', 'stop', 'com.toppatch.agent']
        output, error = _process_cmd(cmd)

    if output:
        print output

    if error:
        print error


def status_agent():

    output = None
    error = None

    if _system == 'darwin':

        cmd = ['launchctl', 'list']
        output, error = _process_cmd(cmd)

    if output:
        print output

    if error:
        print error


def delete_agent():

    while True:
        confirmation = raw_input(
            'Are you sure you want to delete the daemon script? (yes/no)  '
        )

        if confirmation.lower() == 'yes':
            break

        elif confirmation.lower() == 'no':
            print 'Not deleting daemon script.'
            return

        else:
            print "Please type 'yes' or 'no'."

    output = None
    error = None

    if _system == 'darwin':

        cmd = ['launchctl', 'list']
        output, error = _process_cmd(cmd)

    if output:
        print output

    if error:
        print error


if __name__== "__main__":


    parser = argparse.ArgumentParser(
        description="Admin tool for the TopPatch Agent. Must be run as root."
    )
    parser.add_argument(
        '-start',
        action="store_true",
        help='Starts the agent daemon.'
    )

    parser.add_argument(
        '-stop',
        action="store_true",
        help='Stops the agent daemon.'
    )

    parser.add_argument(
        '-restart',
        action="store_true",
        help='Restarts the agent daemon.'
    )

    parser.add_argument(
        '-delete',
        action="store_true",
        help=(
            'Deletes the daemon script.'
            '(ie: On OSX the plist; On Linux the init.d script)'
        )
    )
    args = parser.parse_args()

    # if os.geteuid() != 0:
    #         sys.exit("The agent admin must be run as root.")

    if args.start:
        print args.start

    elif args.stop:
        print args.stop

    elif args.restart:
        print args.restart

    elif args.delete:
        delete_agent()

    else:
        print (
            'Please provide a valid action to perform: %s ' %
            '(-start, -stop, -restart, -delete)'
        )


