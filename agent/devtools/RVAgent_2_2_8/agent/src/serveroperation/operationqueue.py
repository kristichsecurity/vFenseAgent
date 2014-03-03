import Queue

from utils import logger


class OperationQueue():
    """ Simple queue specifically for server operations.
    """

    def __init__(self):

        self.queue = Queue.Queue()

        self.op_in_progress = False
        self.paused = False

    def queue_dump(self):
        return [op for op in self.queue.queue]

    def remove(self, operation):
        try:
            self.queue.queue.remove(operation)

            return True
        except Exception as e:
            logger.error("Failed to remove operation from queue: {0}"
                         .format(operation))
            logger.exception(e)

            return False

    def put_non_duplicate(self, operation):
        """
        Put the operation in queue if no other operation of the same type
        exists.
        """
        if operation.type in [op.type for op in self.queue_dump()]:
            return False

        return self.put(operation)

    def put(self, operation):
        """
        Attempts to add an item to the queue.
        @param operation: Item to be added.
        @return: True if item was successfully added, false otherwise.
        """
        result = False

        try:

            if operation:

                self.queue.put(operation)
                result = True

                try:
                    logger.debug(
                        "Added {0} / {1} to OpQueue."
                        .format(operation.type, operation.id)
                    )
                except Exception:
                    logger.debug(
                        "Added {0} to OpQueue."
                        .format(operation)
                    )

        except Queue.Full as e:

            logger.error("Agent is busy. Ignoring operation.")
            result = False

        except Exception as e:

            logger.error("Error adding operation to queue.")
            logger.error("Message: %s" % e)
            result = False

        return result

    def get(self):
        """
        Attempts to get an operation from the queue if no operation is pending.

        Returns:
            The operation if it was successfully retrieved, None otherwise.

        """
        operation = None

        if (not self.op_in_progress) and (not self.paused):

            try:
                operation = self.queue.get_nowait()
                self.op_in_progress = True

                try:
                    logger.debug(
                        "Popping {0} from OpQueue.".format(operation.id)
                    )
                except Exception:
                    logger.debug("Popping {0} from OpQueue.".format(operation))

            except Queue.Empty as e:
#                logger.debug("Operations queue is empty.")
                operation = None

            except Exception as e:
                logger.error("Error accessing operation queue.")
                logger.error("Message: %s" % e)
                operation = None

        return operation

    def done(self):
        """
        Indicates that an operation is done.
        @return: Nothing
        """

        try:
            self.queue.task_done()
            self.op_in_progress = False
        except Exception as e:
            logger.error("Error marking operation as done.")
            logger.error("Message: %s" % e)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def set_operation_caller(self, callback):
        self.callback = callback

    def _is_op_pending(self, running):
        self.op_in_progress = running
