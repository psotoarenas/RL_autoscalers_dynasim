
class MicroserviceDataClass:
    def __init__(self, name):
        self.name = name
        self.state = 'UNKNOWN'
        self.server = None
        self.cpu_usage = 0.0
        self.overflow = 0.0

    def update_state(self, new_state):
        self.state = new_state

    def update_cpu_usage(self, new_cpu_usage):
        self.cpu_usage = new_cpu_usage

    def update_overflow(self, new_overflow):
        self.overflow = new_overflow

    def update_server(self, new_server):
        self.server = new_server