#!/usr/bin/env python
#-*- coding: utf-8 -*-
import os
import re
import sys
import time
import threading
import subprocess

from threading import Thread

from PyQt4 import QtCore, QtGui, QtDeclarative, QtNetwork

CURRENT_DIR = os.path.dirname(sys.executable)
#CURRENT_DIR = os.path.dirname(__file__)

NAME_OF_APP = "TopPatch Agent Installer.app"
#PARENT_DIR = None

class MainWindow(QtDeclarative.QDeclarativeView):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.init_ui()
        # Needs to be created in order to be used by the qml
        self.installer_functions = InstallerFunctions(self.rootObject())

    def init_ui(self):
        self.setWindowTitle("TopPatch Agent Installer")
        self.setSource(
            QtCore.QUrl(os.path.join(CURRENT_DIR, 'InstallWindow.qml'))
        )
        self.setResizeMode(QtDeclarative.QDeclarativeView.SizeViewToRootObject)
        self.center()

    def center(self):
        geom = self.frameGeometry()
        screen_center = QtGui.QDesktopWidget().availableGeometry().center()
        geom.moveCenter(screen_center)
        self.move(geom.topLeft())

    def exit_handler(self):
        if self.installer_functions.install_thread:
            if self.installer_functions.install_thread.is_alive():
                self.installer_functions.install_thread.stop()


class ErrorWindow(QtDeclarative.QDeclarativeView):
    class CommunicateError(QtCore.QObject):
        err_signal = QtCore.pyqtSignal('QString')

    def __init__(self, error_message, parent=None):
        super(ErrorWindow, self).__init__(parent)
        self.error_message = error_message

        self.init_ui()
        self.init_signals()
        self.show_error()

    def init_ui(self):
        self.setWindowTitle("TopPatch Agent Install Error")
        self.setSource(
            QtCore.QUrl(os.path.join(CURRENT_DIR, 'ErrorWindow.qml'))
        )
        self.setResizeMode(QtDeclarative.QDeclarativeView.SizeViewToRootObject)

    def init_signals(self):
        self.root = self.rootObject()
        self.root.closeWindow.connect(self.close)

        self.error_message_signal = self.CommunicateError()
        self.error_message_signal.err_signal.connect(
            self.root.changeErrorMessage
        )

    def show_error(self):
        self.error_message_signal.err_signal.emit(self.error_message)


class InstallerFunctions(QtCore.QObject):
    class pyqtSignal(QtCore.QObject):
        result = QtCore.pyqtSignal('QString')

    class InstallThread(threading.Thread):
        def __init__(self, install_result_signal, username, password, serverAddress, customer):
            threading.Thread.__init__(self)

            self.install_result_signal = install_result_signal
            self.process = None

            self.working_dir = os.path.join(CURRENT_DIR, '../Resources')
            self.install_script = os.path.join(self.working_dir, 'agent/agent_utils')

            self.username = self._surround(str(username))
            self.password = self._surround(str(password))
            self.serverAddress = self._surround(str(serverAddress))
            self.customer = self._surround(str(customer))

        def _surround(self, text):
            return "'" + text + "'"

        def _get_address_option(self, serverAddress):
            # TODO: maybe regex match ipv6?
            if ':' in serverAddress:
                return '-i'
            elif re.search(r'^\d{0,3}\.\d{0,3}\.\d{0,3}\.\d{0,3}$', serverAddress):
                return '-i'
            else:
                return '-s'

        def run(self):
            self._install_cmd()

        def stop(self):
            if self.process:
                self.process.terminate()

        def _install_cmd(self):
            address_option = \
                self._surround(self._get_address_option(self.serverAddress))

            install_script = self._surround(self.install_script)
            working_dir = self._surround(self.working_dir)

            # Change the argument to workingdir so that it points to the parent
            # directory of the agent directory
            cmd = [install_script, '-u', self.username, '-p', self.password,
                   address_option, self.serverAddress, '-c', self.customer,
                   '--workingdir', working_dir]

            osas_cmd = ['osascript', '-e', 'do shell script \"%s\" with administrator privileges' % ' '.join(cmd)]

            self.process = subprocess.Popen(
                osas_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            out, err = self.process.communicate()

            # AppleScript likes to replace \n with \r for stderr
            err = err.replace('\r', '\n')

            self.install_result_signal.result.emit(err)

    def __init__(self, main_root):
        QtCore.QObject.__init__(self)
        self.main_root = main_root
        self.install_thread = None

        self.init_signals()

    def init_signals(self):
        self.install_result_signal = self.pyqtSignal()
        self.install_result_signal.result.connect(self.main_root.installResult)

        self.main_root.installAgent.connect(self.install)
        self.main_root.installError.connect(self.install_error)

    @QtCore.pyqtSlot('QString', 'QString', 'QString', 'QString')
    def install(self, username, password, serverAddress, customer):
        self.install_thread = self.InstallThread(
            self.install_result_signal,
            username,
            password,
            serverAddress,
            customer
        )
        self.install_thread.start()

    @QtCore.pyqtSlot('QString')
    def install_error(self, error_message):
        self.error_window = ErrorWindow(error_message)

        # Place this window's center in the center of the main window
        main_center_x = main_window.x() + (main_window.width() / 2)
        main_center_y = main_window.y() + (main_window.height() / 2)
        x = main_center_x - (self.error_window.width() / 2)
        y = main_center_y - (self.error_window.height() / 2)

        self.error_window.move(x, y)
        self.error_window.show()
        # Bring to the font
        self.error_window.raise_()


if __name__ == '__main__':
    split_dirs = CURRENT_DIR.split('/')
    #PARENT_DIR = '/'.join(split_dirs[0:split_dirs.index(NAME_OF_APP)])

    app = QtGui.QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()
    # Bring to the font
    main_window.raise_()

    app.aboutToQuit.connect(main_window.exit_handler)

    sys.exit(app.exec_())
