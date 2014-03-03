#!/usr/bin/env python
import os
import sys
import time
import signal
import subprocess

PIDFILE = '/tmp/toppatch_watcher.pid'
PATH='/opt/TopPatch/agent/'
TOPPATCHWATCHER = 'watcher.py'
PROGRAM = 'python'

# Return codes
# If changes are made here, please update them in:
# serveroperation/starteropmanager/ServiceProcess
UNKNOWN_ERROR = -2
FORK_FAILED = -1
SUCCESS = 0
AGENT_ALREADY_RUNNING = 1
AGENT_ALREADY_STOPPED = 2
PID_EXIST_NO_PROCESS = 3

UNKNOWN_OPTION = 5


def run(program, *args):
    try:
        pid = os.fork()
        if not pid:
            os.execvp(program, (program,) + args)
    except OSError, e:
        sys.stderr.write("fork failed %d (%s)\n" % (e.errno, e.strerror))
        # logger.warning("fork failed %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(FORK_FAILED)
    return pid


def handler(signum, frame):
    print "returning back to terminal"


def start():
    pids = []
    if os.path.isfile(PIDFILE):
        pf = file(PIDFILE, 'r')
        pids = (pf.read().strip()[1:-1])
        pid_no = pids.split(', ')
        pf.close()

        p = subprocess.Popen(['ps -fe |grep %s|grep -v grep' % pid_no[0]],
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        if p.stdout.read() == '':
            os.remove(PIDFILE)
            start()
        else:
            count = 0
            for pid in pid_no:
                if pid:
                    count += 1
            if count == len(pid_no):
                message = "TopPatch Starter is already running. Pid: %s(%s)\n" %\
                          (pids, PIDFILE)

                sys.stderr.write(message)
                sys.exit(AGENT_ALREADY_RUNNING)
    else:
        os.chdir(PATH)
        pid = run(PROGRAM, TOPPATCHWATCHER)
        pids.append(pid)
        time.sleep(1)
        file(PIDFILE, 'w+').write("%s\n" % pids)
        signal.signal(signal.SIGINT, handler)
        time.sleep(5)
        print 'TopPatch Starter is running.'


def stop():
    if not os.path.isfile(PIDFILE):
        message = "TopPatch Starter is not running.\n"
        sys.stderr.write(message)
        sys.exit(AGENT_ALREADY_STOPPED)

    else:
        try:
            pf = file(PIDFILE, 'r')
            pids = (pf.read().strip()[1:-1])
            pid_no = pids.split(', ')
            pf.close()

            if pid_no is '':
                raise Exception("Pid file didn't return an integer.")

            os.kill(int(pid_no[0]), signal.SIGTERM)
            time.sleep(2)
            os.remove(PIDFILE)

            print 'TopPatch Starter has been stopped.'

        except OSError as e:
            print 'PID exist but now process. Removing.'
            os.remove(PIDFILE)
            sys.exit(PID_EXIST_NO_PROCESS)

        except Exception as e:
            print e.message
            os.remove(PIDFILE)
            sys.exit(UNKNOWN_ERROR)


def restart():
    stop()
    print "\n"
    start()


def status():
    if os.path.isfile(PIDFILE):
        message = "TopPatch Starter is running. PIDFILE: '%s'\n"
        sys.stderr.write(message % PIDFILE)
        # logger.info(message % PIDFILE)
        sys.exit(AGENT_ALREADY_RUNNING)
    else:
        print "TopPatch Starter is not running."
        sys.exit(AGENT_ALREADY_STOPPED)

ACTION = sys.argv[1]

if __name__ == "__main__":
    if len(sys.argv) == 2:
        if ACTION == 'start':
            start()
        elif ACTION == 'stop':
            stop()
        elif ACTION == 'restart':
            restart()
        elif ACTION == 'status':
            status()
        else:
            print "%s is not a valid option." % ACTION
            print "usage: %s start|stop|restart|status" % sys.argv[0]
            sys.exit(UNKNOWN_OPTION)

        sys.exit(SUCCESS)
    else:
        print "usage: %s start|stop|restart|status" % sys.argv[0]
