import threading
import time
import x_pb2
import random


class RewardAdversarial:
    def __init__(self):
        self.distribution_period = 'uniform'
        self.distribution_execution_time = 'uniform'
        self.period_params = [100]
        self.execution_time_params = [1]

    def getUpdate(self):
        toSimMessage = x_pb2.ToSimulationMessage()
        message = x_pb2.TrafficGeneratorParameters()
        message.distribution_period = self.distribution_period
        message.distribution_execution_time = self.distribution_execution_time
        message.parameters_period.extend(self.period_params)
        message.parameters_execution_time.extend(self.execution_time_params)
        return toSimMessage.traffic_generator_params.CopyFrom(message)

    def updateParams(self):
        while True:
            if self.period_params[0] == 100:
                self.period_params = [10]
            else:
                self.period_params = [100]

            if self.execution_time_params[0] == 1:
                self.execution_time_params = [1]
            else:
                self.execution_time_params = [1]
            time.sleep(0.5)

    def run(self):
        x = threading.Thread(target=self.updateParams)
        x.start()