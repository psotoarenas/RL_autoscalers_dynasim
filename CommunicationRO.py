import x_pb2
from Communicator import Communicator
from RewardAdversarial import RewardAdversarial
from TimeManagment import TimeManagement
import datetime


class CommunicationRA:
    def __init__(self):
        self._communicator = Communicator(5556, 5557)
        self._communicator.add_notifier(lambda m: self.handle_message(m))

        self._timemanager = TimeManagement()

        self.ra_pid = ''
        self.ra_agent = RewardAdversarial()
        self.ra_agent.run()

    def run(self):
        with self._communicator:
            self._communicator.run()

    def handle_message(self, message: x_pb2.ToPythonMessage):
        # if message.HasField("aimessageclient"):
        #     aimsg = message.aimessageclient
        #     toSimMessage = x_pb2.ToSimulationMessage()
        #     new_msg = x_pb2.AIMessageClient()
        #     new_msg.id = aimsg.id
        #     new_msg.message = aimsg.message
        #     toSimMessage.aimessageclient.CopyFrom(new_msg)
        #     toSimMessage.transfer_id = message.transfer_id
        #     toSimMessage.pid_receiver = message.pid_sender
        #     self._communicator.add_message(toSimMessage)

        self._timemanager.updateTime(message.tick_offset)

        if message.HasField("request"):
            self._communicator.send()

        if message.HasField("info"):
            self._communicator.set_push_socket(message.info.ipaddress)
            self._timemanager.initializeTime(message.info.tick_length)

        if message.HasField("register_communicator"):
            print(message)
            self.ra_pid = message.register_communicator.pid

        if message.HasField("counters"):
            print(message)


if __name__ == "__main__":
    messagehandler = CommunicationRA()
    messagehandler.run()
