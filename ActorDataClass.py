
class MicroserviceDataClass:
    def __init__(self, name):
        self.name = name
        self.state = 'UNKNOWN'
        self.server = None
        self.cpu_usage = 0.0
        self.overflow = 0.0


class LoadbalancerDataClass (MicroserviceDataClass):
    def __init__(self, name):
        super().__init__(name)
        self.weights = {}
        self.weights_state = {}
        self.last_update = -1


class ServerDataClass:
    def __init__(self, name):
        self.name = name
        self.cpu_usage = 0.0
        self.ms_list = []
        self.state = 'UNKNOWN'


class ClientGeneratorDataClass:
    def __init__(self, name):
        self.name = name


