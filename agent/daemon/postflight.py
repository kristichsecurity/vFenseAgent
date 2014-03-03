#!/usr/bin/python

import sys
import os
import shutil
import subprocess


system_daemon_dir = '/System/Library/LaunchDaemons/'
agent_daemon_dir = '/opt/TopPatch/agent/daemon/'

agent_plist_filename = 'com.toppatch.agent.plist'
watcher_plist_filename = 'com.toppatch.watcher.plist'

agent_plist_path = os.path.join(agent_daemon_dir, agent_plist_filename)
watcher_plist_path = os.path.join(agent_daemon_dir, watcher_plist_filename)

system_agent_path = os.path.join(system_daemon_dir, agent_plist_filename)
system_watcher_path = os.path.join(system_daemon_dir, watcher_plist_filename)

load_command = ['/bin/launchctl', 'load', '-w']
unload_command = ['/bin/launchctl', 'unload', '-w']

# Check if plist file exist first. Unload it if present.

if os.path.exists(system_agent_path):

    try:

        unload_command.append(system_agent_path)

        process = subprocess.Popen(unload_command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        raw_output, error_output = process.communicate()

        os.remove(system_agent_path)

        unload_command.remove(system_agent_path)

    except Exception as e:

        print 'Could not remove {}. Exiting'.format(system_agent_path)
        sys.exit(-1)


# Copy the plist file over to the system's daemon directory and load it.
shutil.copy2(agent_plist_path, system_daemon_dir)

load_command.append(system_agent_path)

process = subprocess.Popen(load_command, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)

raw_output, error_output = process.communicate()

load_command.remove(system_agent_path)
