import x_pb2
from Communicator import Communicator
from TimeManagment import TimeManagement
from RewardOptimizer import RewardOptimizer
import datetime


class CommunicationRA:
    def __init__(self):
        self._communicator = Communicator(5556, 5557)
        self._communicator.add_notifier(lambda m: self.handle_message(m))
        self.timemanager = TimeManagement()

        self.ro_pid = ''
        self.ro_agent = RewardOptimizer(self.timemanager)
        self.ro_agent.run()

    def run(self):
        with self._communicator:
            self._communicator.run()

    def handle_message(self, message: x_pb2.ToPythonMessage):
        self.timemanager.updateTime(message.tick_offset)

        if message.HasField("info"):
            self._communicator.set_push_socket(message.info.ipaddress)
            self.timemanager.initializeTime(message.info.tick_length)

        if message.HasField("register_communicator"):
            #print(message)
            self.ro_pid = message.register_communicator.pid

        if message.HasField("counters"):
            for counter in message.counters.counters:
                self.ro_agent.add_counter(counter)

            if self.ro_pid != '':
                messageToAdd = self.ro_agent.getUpdate()
                if messageToAdd:
                    self._communicator.add_message(messageToAdd, self.ro_pid)
                self._communicator.send()


if __name__ == "__main__":
    messagehandler = CommunicationRA()
    messagehandler.run()
