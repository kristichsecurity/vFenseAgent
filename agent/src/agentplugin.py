import sys


def _functionId(obj, nFramesUp):
    """ Create a string naming the function n frames up on the stack.
    """
    fr = sys._getframe(nFramesUp+1)
    co = fr.f_code
    return "%s.%s" % (obj.__class__, co.co_name)


def abstract_method(obj=None):
    """ Use this instead of 'pass' for the body of abstract methods.
    """
    raise NotImplementedError("Unimplemented abstract method: %s" %
                              _functionId(obj, 1))


class AgentPlugin:
    """
    Used as an abstract interface for agent plugins. All methods within must be
    implemented, otherwise a NotImplementedError exception is raised.
    """

    def start(self):
        """ Runs once the agent core is initialized.
        @return: Nothing
        """
        abstract_method(self)

    def stop(self):
        """ Runs once the agent core is shutting down.
        @return: Nothing
        """
        abstract_method(self)

    def run_operation(self, operation):
        """ Executes an operation given to it by the agent core.
        @requires: Nothing
        """
        abstract_method(self)

    def initial_data(self):
        """ Any initial data the server should have on first run.
        @requires: Nothing
        """
        abstract_method(self)

    def name(self):
        """ Retrieves the name for this plugin.
        @return: Nothing
        """
        abstract_method(self)

    def send_results_callback(self, callback):
        """ Sets the callback used to send results back to the server.
        @requires: Nothing
        """
        abstract_method(self)

    def register_operation_callback(self, callback):
        """ Sets the callback used to register/save operations with the agent
        core.
        @requires: Nothing
        """
        abstract_method(self)