
class MicroserviceDataClass:
    def __init__(self, name):
        self.name = name
        self.state = 'UNKNOWN'
        self.server = None
        self.cpu_usage = 0.0
        self.overflow = 0.0
        self.peak_latency = 0.0
