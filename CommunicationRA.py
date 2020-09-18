import x_pb2
from Communicator import Communicator
from RewardAdversarial import RewardAdversarial
from TimeManagment import TimeManagement
import datetime


class CommunicationRA:
    def __init__(self):
        self._communicator = Communicator(5558, 5559)
        self._communicator.add_notifier(lambda m: self.handle_message(m))

        self._timemanager = TimeManagement()

        self.ra_pid = ''
        self.ra_agent = RewardAdversarial()
        self.ra_agent.run()

    def run(self):
        with self._communicator:
            self._communicator.run()

    def handle_message(self, message: x_pb2.ToPythonMessage):
        self._timemanager.updateTime(message.tick_offset)

        if message.HasField("counters"):
            if self.ra_pid != '':
                messageToAdd = self.ra_agent.getUpdate()
                if messageToAdd:
                    self._communicator.add_message(messageToAdd, self.ra_pid)
            self._communicator.send()

        if message.HasField("info"):
            self._communicator.set_push_socket(message.info.ipaddress)
            self._timemanager.initializeTime(message.info.tick_length)

        if message.HasField("register_communicator"):
            self.ra_pid = message.register_communicator.pid

if __name__ == "__main__":
    messagehandler = CommunicationRA()
    messagehandler.run()
