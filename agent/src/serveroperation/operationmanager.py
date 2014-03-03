import time
import os
import subprocess
import datetime
import json


from net import netmanager
from threading import Thread
from data.sqlitemanager import SqliteManager
from utils import systeminfo, settings, logger, queuesave
from serveroperation.sofoperation import SofOperation, SelfGeneratedOpId
from serveroperation.sofoperation import OperationKey, OperationValue, CoreUrn
from serveroperation.sofoperation import ResultOperation, RequestMethod


class OperationManager():

    def __init__(self, plugins):
        # Must be called first! Especially before any sqlite stuff.
        self._sqlite = SqliteManager()

        self._plugins = plugins
        self._load_plugin_handlers()

        self._operation_queue = queuesave.load_operation_queue()
        self._result_queue = queuesave.load_result_queue()

        operation_queue_thread = Thread(target=self._operation_queue_loop)
        operation_queue_thread.daemon = True
        operation_queue_thread.start()

        result_queue_thread = Thread(target=self._result_queue_loop)
        result_queue_thread.daemon = True
        result_queue_thread.start()

        self._send_results = None

        self._uptime_file = os.path.join(settings.EtcDirectory, '.last_uptime')

    def _load_plugin_handlers(self):

        for plugin in self._plugins.values():

            plugin.send_results_callback(self.add_to_result_queue)
            plugin.register_operation_callback(self.register_plugin_operation)

    def _save_and_send_results(self, operation):

        # Check for self assigned operation IDs and send emtpy string
        # to server if present.
        op_id = operation.id
        if SelfGeneratedOpId in operation.id:
            operation.id = ""

        #logger.debug("*** RAW RESULT: {0}".format(operation.raw_result))

        # TODO: remove
        #v = json.loads(operation.raw_result)
        #print json.dumps(v, indent=4)

        result = self._send_results(
            operation.raw_result,
            operation.urn_response,
            operation.request_method
        )

        operation.id = op_id

        # Result was actually sent, write to db
        if result:
            self._sqlite.add_result(operation, result, datetime.datetime.now())

        return result

    def register_plugin_operation(self, message):
        """ Provides a way for plugins to store their custom made
        operations with the agent core.

        Args:

            - message: Operation as a JSON formatted string.

        Returns:

            - True if operation was added successfully. False otherwise.
        """

        self.add_to_operation_queue(message)

        return True

    def _major_failure(self, operation, exception):

        if operation:
            root = {}
            root[OperationKey.Operation] = operation.type
            root[OperationKey.OperationId] = operation.id
            root[OperationKey.AgentId] = settings.AgentId

            root['error'] = str(exception)

            operation.raw_result = json.dumps(root)

            self.add_to_result_queue(operation)

        else:
            # TODO: Should we send something back to server?
            logger.critical("Operation is empty in _major_failure")

    ################# THE BIG OPERATION PROCESSOR!! ###########################
    ###########################################################################
    def process_operation(self, operation):

        try:

            if not isinstance(operation, SofOperation):
                operation = SofOperation(operation)

            logger.info(
                "Process the following operation: {0}"
                .format(operation.__dict__)
            )

            self._sqlite.add_operation(operation, datetime.datetime.now())

            operation_methods = {
                OperationValue.SystemInfo: self.system_info_op,
                OperationValue.NewAgent: self.new_agent_op,
                OperationValue.Startup: self.startup_op,
                OperationValue.NewAgentId: self.new_agent_id_op,
                OperationValue.Reboot: self.reboot_op,
                OperationValue.Shutdown: self.shutdown_op
            }

            if operation.type in operation_methods:

                # Call method
                operation_methods[operation.type](operation)

            elif operation.plugin in self._plugins:
                self.plugin_op(operation)

            else:

                raise Exception(
                    'Operation/Plugin {0} was not found.'
                    .format(operation.__dict__)
                )

        except Exception as e:

            logger.error(
                "Error while processing operation: {0}"
                .format(operation.__dict__)
            )
            logger.exception(e)
            self._major_failure(operation, e)

    ###########################################################################
    ###########################################################################

    def system_info_op(self, operation):
        self.add_to_result_queue(self.system_info(operation))

    def new_agent_op(self, operation):
        operation = self._initial_data(operation)
        operation.raw_result = self._initial_formatter(operation)
        operation.urn_response = CoreUrn.get_new_agent_urn()
        operation.request_method = RequestMethod.POST

        try:
            modified_json = json.loads(operation.raw_result)

            # Removing unnecessary keys from JSON
            del modified_json[OperationKey.OperationId]
            del modified_json[OperationKey.AgentId]

            operation.raw_result = json.dumps(modified_json)
        except Exception as e:
            logger.error("Failed to modify new agent operation JSON.")
            logger.exception(e)

        self.add_to_result_queue(operation)

    def startup_op(self, operation):
        operation = self._initial_data(operation)
        operation.raw_result = self._initial_formatter(operation)
        operation.urn_response = CoreUrn.get_startup_urn()
        operation.request_method = RequestMethod.PUT

        self.add_to_result_queue(operation)

    def new_agent_id_op(self, operation):
        self._new_agent_id(operation)

    def reboot_op(self, operation):
        netmanager.allow_checkin = False
        logger.info("Checkin set to: {0}".format(netmanager.allow_checkin))

        # Read by _check_for_reboot
        with open(settings.reboot_file, 'w') as _file:
            _file.write(operation.id)

        self._system_reboot(operation.reboot_delay_seconds / 60)

        reboot_failure_thread = Thread(
            target=self._reboot_failure, args=(operation,)
        )
        reboot_failure_thread.daemon = True
        reboot_failure_thread.start()

    def _reboot_failure(self, operation):
        """
        This method is run on a separate thread, it is only called after
        running the reboot operation. If it completely finishes, it means
        the computer was never rebooted, therefore the operation failed.
        """

        time.sleep(operation.reboot_delay_seconds + 120)

        ###############################################################
        #             *** Reboot should have occured ***              #
        ###############################################################

        self._reboot_result('false', operation.id, "Reboot was cancelled.")

        if os.path.exists(settings.reboot_file):
            os.remove(settings.reboot_file)

        netmanager.allow_checkin = True
        logger.debug("Checkin set to: {0}".format(netmanager.allow_checkin))

    def shutdown_op(self, operation):
        netmanager.allow_checkin = False
        logger.info("Checkin set to: {0}".format(netmanager.allow_checkin))

        # Read by _check_for_shutdown
        with open(settings.shutdown_file, 'w') as _file:
            _file.write(operation.id)

        # This offsets the shutdown by 15 seconds so that the agent check in
        # can occur and dump the operations to file.
        time.sleep(15)

        self._system_shutdown(operation.shutdown_delay_seconds / 60)

        shutdown_failure_thread = Thread(
            target=self._shutdown_failure, args=(operation,)
        )
        shutdown_failure_thread.daemon = True
        shutdown_failure_thread.start()

    def _shutdown_failure(self, operation):
        """
        This method is run on a separate thread, it is only called after
        running the shutdown operation. If it completely finishes, it means
        the computer was never shutdown, therefore the operation failed.
        """

        time.sleep(operation.reboot_delay_seconds + 120)

        ###############################################################
        #            *** Shutdown should have occured ***             #
        ###############################################################

        self._shutdown_result('false', operation.id, "Shutdown was cancelled.")

        if os.path.exists(settings.shutdown_file):
            os.remove(settings.shutdown_file)

        netmanager.allow_checkin = True
        logger.debug("Checkin set to: {0}".format(netmanager.allow_checkin))

    def plugin_op(self, operation):
        self._plugins[operation.plugin].run_operation(operation)

    def _initial_data(self, operation):
        operation.core_data[OperationValue.SystemInfo] = self.system_info()
        operation.core_data[OperationValue.HardwareInfo] = self.hardware_info()

        for plugin in self._plugins.values():
            try:

                plugin_data = plugin.initial_data(operation.type)

                if plugin_data is not None:
                    operation.plugin_data[plugin.name()] = plugin_data

            except Exception as e:

                logger.error(
                    "Could not collect initial data for plugin %s." %
                    plugin.name()
                )
                logger.exception(e)

        return operation

    def _initial_formatter(self, operation):

        root = {}
        root[OperationKey.Operation] = operation.type
        root[OperationKey.Rebooted] = self._is_boot_up()
        root[OperationKey.CustomerName] = settings.Customer

        root[OperationKey.OperationId] = operation.id
        root[OperationKey.AgentId] = settings.AgentId

        #root[OperationKey.Core] = operation.core_data
        root.update(operation.core_data)

        root[OperationKey.Plugins] = operation.plugin_data

        return json.dumps(root)

    def _new_agent_id(self, operation):
        """ This will assign a new agent ID coming from the server.
        @return: Nothing
        """

        _id = operation.json_message[OperationKey.AgentId]
        settings.AgentId = _id
        settings.save_settings()

    def _reboot_result(self, success, operation_id, message=''):
        root = {}
        root[OperationKey.Operation] = OperationValue.Reboot
        root[OperationKey.OperationId] = operation_id
        root[OperationKey.Success] = success
        root[OperationKey.Message] = message

        operation = SofOperation()
        operation.raw_result = json.dumps(root)
        operation.urn_response = CoreUrn.get_reboot_urn()
        operation.request_method = RequestMethod.PUT

        self.add_to_result_queue(operation)

    def _check_for_reboot(self):
        operation_id = ''

        if os.path.exists(settings.reboot_file):

            with open(settings.reboot_file, 'r') as _file:
                operation_id = _file.read()
                operation_id = operation_id.strip()

            # Clear the file in case the agent fails to delete it
            open(settings.reboot_file, 'w').close()

            try:
                os.remove(settings.reboot_file)
            except Exception as e:
                logger.error("Failed to remove reboot file.")
                logger.exception(e)

        if operation_id:
            self._reboot_result('true', operation_id)

    def _shutdown_result(self, success, operation_id, message=''):
        root = {}
        root[OperationKey.Operation] = OperationValue.Shutdown
        root[OperationKey.OperationId] = operation_id
        root[OperationKey.Success] = success
        root[OperationKey.Message] = message

        operation = SofOperation()
        operation.raw_result = json.dumps(root)
        operation.urn_response = CoreUrn.get_shutdown_urn()
        operation.request_method = RequestMethod.PUT

        self.add_to_result_queue(operation)

    def _check_for_shutdown(self):
        operation_id = ''

        if os.path.exists(settings.shutdown_file):

            with open(settings.shutdown_file, 'r') as _file:
                operation_id = _file.read()
                operation_id = operation_id.strip()

            # Clear the file in case the agent fails to delete it
            open(settings.shutdown_file, 'w').close()

            try:
                os.remove(settings.shutdown_file)
            except Exception as e:
                logger.error("Failed to remove shutdown file.")
                logger.exception(e)

        if operation_id:
            self._shutdown_result('true', operation_id)

    def initial_data_sender(self):

        logger.info("Sending initial data.")

        operation = SofOperation()

        if settings.AgentId != "":
            self._check_for_reboot()
            self._check_for_shutdown()

            operation.type = OperationValue.Startup

        else:
            operation.type = OperationValue.NewAgent

        self.process_operation(operation.to_json())

    def send_results_callback(self, callback):
        self._send_results = callback

    def _plugin_not_found(self, operation):
        """
        Used when an operation needs a specific plugin which is not
        on the current machine. Notifies the server as well.
        """

        logger.error("No plugin support found")
        self._major_failure(operation, Exception("No plugin support found"))

    def operation_queue_file_dump(self):
        try:
            queuesave.save_operation_queue(self._operation_queue)
        except Exception as e:
            logger.error("Failed to save operation queue to file.")
            logger.exception(e)

    def add_to_operation_queue(self, operation):
        """
        Put the operation to file.

        Args:
            operation - The actual operation.

            no_duplicate - Will not put the operation in the queue if there
                           already exists an operation of the same type in
                           queue.

        Returns:
            (bool) True if able to put the operation in queue, False otherwise.

        """

        #if no_duplicate:
        #    return self._operation_queue.put_non_duplicate(operation)

        return self._operation_queue.put(operation)

    def _operation_queue_loop(self):

        while True:
            self.operation_queue_file_dump()

            try:
                operation = self._operation_queue.get()
                if operation:
                    self.process_operation(operation)
                    self._operation_queue.done()

                else:
                    # Only sleep if there is nothing in the queue.
                    # Keep banging (pause) them out!
                    time.sleep(4)

            except Exception as e:
                logger.error("Failure in operation queue loop.")
                logger.exception(e)

    def result_queue_file_dump(self):
        try:
            queuesave.save_result_queue(self._result_queue)

        except Exception as e:
            logger.error("Failed to save result queue to file.")
            logger.exception(e)

    def _result_queue_loop(self):

        while True:
            self.result_queue_file_dump()

            queue_dump = self._result_queue.queue_dump()

            should_send = [result_op for result_op in queue_dump
                           if result_op.should_be_sent()]

            if should_send:

                logger.debug("Results to be sent: {0}".format(should_send))

                for result_op in should_send:
                    # TODO: what should be done if fails to remove?
                    self._result_queue.remove(result_op)
                    self.process_result_operation(result_op)

                self._result_queue.done()

            else:
                #logger.debug(
                #    "Results in queue: {0}".format(queue_dump)
                #)
                time.sleep(4)

    def process_result_operation(self, result_operation):
        """ Attempts to send the results in the result queue. """

        operation = result_operation.operation

        if result_operation.should_be_sent():
            # No result means it hasn't been processed, no urn_response
            # means unknown operation was received from server.
            if (operation.raw_result != settings.EmptyValue and
                    operation.urn_response and operation.request_method):

                # Operation has been processed, send results to server
                if (not self._save_and_send_results(operation) and
                        result_operation.retry):
                    # Time this out for a few
                    result_operation.timeout()

                    # Failed to send result, place back in queue
                    self.add_to_result_queue(result_operation)
            else:
                logger.debug(("Operation has not been processed, or"
                              " unknown operation was received."))
        else:
            self.add_to_result_queue(result_operation)

    def add_to_result_queue(self, result_operation, retry=True):
        """
        Adds an operation to the result queue which sends it off to the server.

        Arguments:

        result_operation
            An operation which must have a raw_result, urn_response,
            and request_method attribute.

        retry
            Determines if the result queue should continue attempting to send
            the operation to the server in case of a non 200 response.

        """

        try:
            if not isinstance(result_operation, ResultOperation):
                result_operation = ResultOperation(result_operation, retry)

            return self._result_queue.put(result_operation)

        except Exception as e:
            logger.error("Failed to add result to queue.")
            logger.exception(e)

    def server_response_processor(self, message):

        if message:

            for op in message.get('data', []):

                # Loading operation for server in order for the queue
                # dump to know if an operation is savable to file.

                try:

                    operation = SofOperation(json.dumps(op))
                    self.add_to_operation_queue(operation)

                except Exception as e:
                    logger.debug(
                        "Failed to create operation from: {0}".format(op)
                    )
                    logger.exception(e)

        self._save_uptime()

    def system_info(self):

        root = {}
        root['os_code'] = systeminfo.code()
        root['os_string'] = systeminfo.name()
        root['version'] = systeminfo.version()
        root['bit_type'] = systeminfo.bit_type()
        root['computer_name'] = systeminfo.computer_name()
        root['host_name'] = ''  # TODO(urgent): Implement

        logger.debug("System info sent: {0}".format(json.dumps(root)))

        return root

    def hardware_info(self):
        hardware_info = systeminfo.hardware()

        logger.debug("Hardware info sent: {0}".format(hardware_info))

        return hardware_info

    def _system_reboot(self, delay_minutes):

        self._save_uptime()

        warning = "In %s minute(s), this computer will be restarted " \
                  "on behalf of the TopPatch Server." % delay_minutes

        subprocess.call(
            ['/sbin/shutdown', '-r', '+%s' % delay_minutes, warning]
        )

    def _system_shutdown(self, delay_minutes):
        self._save_uptime()

        warning = "In %s minute(s), this computer will be shutdown " \
                  "on behalf of the TopPatch Server." % delay_minutes

        subprocess.call(
            ['/sbin/shutdown', '-h', '+%s' % delay_minutes, warning]
        )

    def _save_uptime(self):
        """Saves the current uptime to a simple text file in seconds.

        Returns:
            Nothing
        """

        uptime = systeminfo.uptime()

        if os.path.exists(self._uptime_file):
            os.remove(self._uptime_file)

        with open(self._uptime_file, 'w') as f:
            f.write(str(uptime))

    def _is_boot_up(self):
        """Checks whether if the agent is coming up because of a reboot or not.

        Returns:
            (bool) True if system boot up detected, False otherwise.
        """

        current_uptime = systeminfo.uptime()
        boot_up = 'no'

        try:
            if os.path.exists(self._uptime_file):

                with open(self._uptime_file, 'r') as f:
                    file_uptime = f.read()

                    if current_uptime < long(file_uptime):

                        boot_up = 'yes'

        except Exception as e:

            logger.error("Could not verify system bootup.")
            logger.exception(e)

        return boot_up
