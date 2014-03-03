import os

from agentplugin import AgentPlugin
from serveroperation.sofoperation import RequestMethod
from net import tunnels
from utils import logger, settings

from ra import formatter
from ra import vine
from ra.raoperation import RaOperation, RaValue, RaUrn


class RaPlugin(AgentPlugin):

    Name = 'ra'

    def __init__(self):

        self._name = RaPlugin.Name

        tunnels.create_keys()

    def start(self):
        """Runs once the agent core is initialized.
        """
        pass

    def stop(self):
        """Runs once the agent core is shutting down.
        """
        pass

    def run_operation(self, operation):
        """ Executes an operation given to it by the agent core.
        """

        try:

            if not isinstance(operation, RaOperation):
                operation = RaOperation(operation.raw_operation)

            operation_methods = {

                RaValue.StartRemoteDesktop: self._start_remote_desktop,
                RaValue.StopRemoteDesktop: self._stop_remote_desktop,
                RaValue.RemoteDesktopPassword: self._set_rd_password,

            }

            operation = operation_methods[operation.type](operation)
            self._send_results(operation)

        except KeyError as e:

            msg = "Received unrecognized operation. Ignoring."
            logger.error(msg)
            logger.exception(e)
            raise Exception(msg)

    def _set_rd_password(self, operation):

        logger.info('Setting remote desktop password.')
        operation.urn_response = RaUrn.RdResults
        operation.request_method = RequestMethod.POST

        error = ''

        try:

            result, error = vine.save_password(operation.password)

            if result:

                operation.success = True
                operation.error = ""

            else:

                operation.success = False
                operation.error = error

        except Exception as e:

            operation.success = False
            operation.error = "Unable to set password: %s" % str(e)
            if error:
                operation.error += error

            logger.error(operation.error)
            logger.exception(e)

        finally:

            operation.raw_result = formatter.rd_results(operation)

        logger.info('Done.')
        return operation

    def _start_remote_desktop(self, operation):

        logger.info('Starting remote desktop.')
        operation.urn_response = RaUrn.RdResults
        operation.request_method = RequestMethod.POST

        vine_running = False

        local_port = tunnels.get_available_port()

        if local_port:

            vine_running, error = vine.start(local_port)

        else:
            # No local port available!?
            operation.success = False
            operation.error = 'No local port available. How did this happen?!'

        if vine_running:

            if operation.tunnel_needed:

                operation.success, operation.error = (
                    tunnels.create_reverse_tunnel(
                        local_port,
                        operation.host_port,
                        settings.ServerAddress,
                        operation.ssh_port
                    )
                )

                if not operation.success:
                    vine.stop()

        operation.raw_result = formatter.rd_results(operation)
        # TODO: Fix ugly response hack. Formetter should go here...
        #operation.raw_result = json.dumps({
        #    'plugin': 'ra',
        #    'host_port': operation.host_port,
        #    'agent_id': settings.AgentId,
        #    'operation': operation.type,
        #    'operation_id': operation.id,
        #    'error': error,
        #})

        logger.info('Done.')
        return operation

    def _stop_remote_desktop(self, operation):

        logger.info('Stopping remote desktop')
        operation.urn_response = RaUrn.RdResults
        operation.request_method = RequestMethod.POST

        operation.success = True

        res, msg = vine.stop()

        if not res:
            operation.success = False
            operation.error = 'Unable to stop vine server.'
            operation.error += msg

        if not tunnels.stop_reverse_tunnel():
            operation.success = False
            operation.error += 'Unable to stop revere tunnel.'

        operation.raw_result = formatter.rd_stop_results(operation)

        logger.info('Done.')
        return operation

    def initial_data(self, operation_type):
        """
        Any initial data the server should have on first run.

        Args:
            operation_type - The type of operation determines what the plugin
                             should return. Currently ignored for RAPlugin.

        Returns:
            (dict) Dictionary with initial RA plugin data.

        """

        logger.debug("Sending initial ra data.")

        data = {
            'public_key': ''
        }

        try:

            if os.path.exists(tunnels.tunnel_pub_key):

                with open(tunnels.tunnel_pub_key, 'r') as pub_key:

                    data = {
                        'public_key': pub_key.read()
                    }

        except Exception as e:

            logger.error('Could not verfiy tunnel key. Not good.')
            logger.exception(e)

        logger.debug("Done with initial ra data.")

        return data

    def name(self):
        """ Retrieves the name for this plugin.
        """

        return self._name

    def send_results_callback(self, callback):
        """ Sets the callback used to send results back to the server.
        """

        self._send_results = callback

    def register_operation_callback(self, callback):
        """ Sets the callback used to register/save operations with the agent
        core.
        """

        self._register_operation = callback
