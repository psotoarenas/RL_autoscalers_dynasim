import threading
import time
import x_pb2
import random
import TimeManagment


class RewardOptimizer:
    def __init__(self, timemanager):
        self.number_of_ms = 0
        self.timemanager = timemanager
        self.total_cpu_usage = 0.0
        self.total_overflow = 0.0

    def getUpdate(self):
        if self.number_of_ms == 0:
            toSimMessage = x_pb2.ToSimulationMessage()
            message = x_pb2.NotReady()
            message.message = "NotReady"
            toSimMessage.not_ready.CopyFrom(message)
            return toSimMessage
        else:
            cpu_usage = self.total_cpu_usage / self.number_of_ms
            overflow = self.total_overflow / self.number_of_ms
            print("#MS: {}".format(self.number_of_ms), end=', ')
            print("Cpu Usage: {:.2f}".format(cpu_usage), end=', ')
            print("Overflow: {:.2f}".format(overflow))

            amount = 0

            if cpu_usage < 0.5 and self.number_of_ms > 1:
                amount = -1
            elif cpu_usage > 0.8:
                amount = 1

            if amount != 0:
                toSimMessage = x_pb2.ToSimulationMessage()
                message = x_pb2.CreateActor()
                message.type = "microservice"
                message.amount = amount
                toSimMessage.create_actor.CopyFrom(message)
                self.number_of_ms = 0
                self.total_cpu_usage = 0.0
                self.total_overflow = 0.0
                return toSimMessage

            self.number_of_ms = 0
            self.total_cpu_usage = 0.0
            self.total_overflow = 0.0

            return

    def add_counter(self, counter):
        if counter.metric == 'cpu_usage':
            self.number_of_ms += 1
            self.total_cpu_usage += counter.value
        elif counter.metric == 'overflow':
            self.total_overflow += counter.value

    def updateParams(self):
        while True:
            time.sleep(0.5)

    def run(self):
        x = threading.Thread(target=self.updateParams)
        x.start()