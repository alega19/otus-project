class BaseTask:

    def __init__(self):
        self.tries = 0

    def handle(self, session, token):
        raise NotImplementedError()

    def cancel(self):
        raise NotImplementedError()
