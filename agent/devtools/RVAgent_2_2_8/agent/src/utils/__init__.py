import threading


class RepeatTimer(threading.Thread):
    """
    A helper class to create a repeating timer.
    threading.Timer is a one time deal.
    """
    def __init__(self, interval, callback, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.interval = interval
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.event = threading.Event()
        self.event.set()

    def run(self):
        while self.event.is_set():
            t = threading.Timer(self.interval, self.callback,
                self.args, self.kwargs)
            t.daemon = True
            t.start()
            t.join()

    def stop(self):
        self.event.clear()
