
import zmq
import x_pb2
import socket


class Communicator:

    def __init__(self, push_port, pull_port):
        self._context = zmq.Context(1)
        self.push_port = push_port
        self.pull_port = pull_port
        self.ai_push = "tcp://localhost:{}".format(push_port)
        self.ip_address = self.get_ip()
        self.ai_pull = "tcp://{}:{}".format(self.ip_address, pull_port)

        self._listen_socket = self._context.socket(zmq.PULL)
        self._speak_socket = self._context.socket(zmq.PUSH)

        self._to_notify = []

        self.response_msgs = x_pb2.ResponseSimulation()

        self._keep_running = False

    def __enter__(self):
        self._listen_socket.bind(self.ai_pull)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._listen_socket.close()
        self._speak_socket.close()

    def add_notifier(self, notifier):
        self._to_notify.append(notifier)

    def run(self):
        self._keep_running = True
        while self._keep_running:
            self._receive()

    def set_push_socket(self, ipaddress):
        ai_push = "tcp://{}:{}".format(ipaddress, self.push_port)
        self._speak_socket.connect(ai_push)
        print(ipaddress)

    def add_message(self, toSimMessage, target):
        toSimMessage.pid_receiver = target
        self.response_msgs.messages.add().CopyFrom(toSimMessage)

    def send(self):
        self._speak_socket.send(self.response_msgs.SerializeToString())
        self.response_msgs = x_pb2.ResponseSimulation()
        self.response_msgs.transfer_id = 1

    def _receive(self):
        result = self._listen_socket.recv()
        message = x_pb2.ToPythonMessage()
        message.ParseFromString(result)

        for c in self._to_notify:
            c(message)

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('8.8.8.8', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP


def print_message(message: x_pb2.ToPythonMessage):
    print(message)


if __name__ == "__main__":
    communicator = Communicator('127.0.0.1',  5558, 5559)
    communicator.add_notifier(print_message)
    print(communicator.get_ip())
    with communicator:
        communicator.run()
