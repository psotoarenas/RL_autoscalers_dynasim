import threading
import time
import x_pb2
import random


class RewardAdversarial:
    def __init__(self, timemanager):
        self.distribution_rate = 'uniform'
        self.distribution_execution_time = 'uniform'
        self.distribution_size = 'exact'
        self.size_params = [300]
        #self.job_list = [433, 348, 950, 481, 25, 896, 156, 191, 674, 261, 897, 419, 950]
        self.job_list = [500]
        self.rate_params = [100]
        self.execution_time_params = [1]
        self.timemanager = timemanager

    def getUpdate(self):
        print(self.timemanager.getCurrentSimulationTime())
        if len(self.job_list):
            new_params = self.job_list.pop(0)
            self.size_params[0] = new_params
        toSimMessage = x_pb2.ToSimulationMessage()
        message = x_pb2.TrafficGeneratorParameters()
        message.distribution_rate = self.distribution_rate
        message.parameters_rate.extend(self.rate_params)

        message.distribution_execution_time = self.distribution_execution_time
        message.parameters_execution_time.extend(self.execution_time_params)

        message.distribution_size = self.distribution_size
        message.parameters_size.extend(self.size_params)
        toSimMessage.traffic_generator_params.CopyFrom(message)
        return [toSimMessage]

    def updateParams(self):
        while True:
            time.sleep(0.5)

    def run(self):
        x = threading.Thread(target=self.updateParams)
        x.start()