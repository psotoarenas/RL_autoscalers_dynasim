import x_pb2
from Communicator import Communicator
from RewardAdversarial import RewardAdversarial


class DecisionMaker:
    def __init__(self):
        self._communicator = Communicator()
        self._communicator.add_notifier(lambda m: self.handle_message(m))

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

        if message.HasField("request"):
            #print(message)
            if self.ra_pid != '':
                messageToAdd = self.ra_agent.getUpdate()
                self._communicator.add_message(messageToAdd, self.ra_pid, "TrafficGeneratorParameters")
            self._communicator.send()

        if message.HasField("info"):
            print(message.info.tick_length)
            self._communicator.set_push_socket(message.info.ipaddress)

        if message.HasField("register_communicator"):
            print(message)
            self.ra_pid = message.register_communicator.pid


if __name__ == "__main__":
    messagehandler = DecisionMaker()
    messagehandler.run()
