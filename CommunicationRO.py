import sys, getopt
import x_pb2
from Communicator import Communicator
from TimeManagment import TimeManagement
from RewardOptimizer import RewardOptimizer
from RO_VerticalScaling import RO_VerticalScaling
from RO_HorizontalScaling import RO_HorizontalScaling
from RO_ServerMigration import RO_ServerMigration
from RO_LoadbalancerWeights import RO_LoadbalancerWeight
import docker


class CommunicationRO:
    def __init__(self, ):
        self._communicator = Communicator(5556, 5557)
        self._communicator.add_notifier(lambda m: self.handle_message(m))
        self.timemanager = TimeManagement()

        self.ro_pid = ''
        self.ro_agent = RO_LoadbalancerWeight(self.timemanager)
        self.ro_agent.run()

    def run(self):
        with self._communicator:
            self._communicator.run()

    def handle_message(self, message: x_pb2.ToPythonMessage):
        self.timemanager.updateTime(message.tick_offset)

        if message.HasField("info"):
            print(message)
            #self._communicator.set_push_socket('143.129.83.93')
            self._communicator.set_push_socket(message.info.ipaddress)
            self.timemanager.initializeTime(message.info.tick_length)

        if message.HasField("register_communicator"):
            #print(message)
            self.ro_pid = message.register_communicator.pid

        if message.HasField("counters"):
            for counter in message.counters.counters_float:
                self.ro_agent.add_counter(counter)

            for counter in message.counters.counters_string:
                self.ro_agent.add_counter(counter)

            if self.ro_pid != '':
                messages = self.ro_agent.getUpdate()
                if messages is not None:
                    for message_sim in messages:
                        self._communicator.add_message(message_sim, self.ro_pid)
                self._communicator.send()

    def start_simulation(self, sim_length, tick_freq=1, report_ticks=1, ip="127.0.0.1",
                         cwd="../dynamicsim/mock-simulators/dynaSim/test/"):
        client_remote = docker.DockerClient(base_url='ssh://ydebock@143.129.83.93', use_ssh_client=False)

        container = client_remote.containers.run(image='gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration',
                           environment={'LENGTH': 1200, 'tickspersecond': 1, 'IP_PYTHON': '143.129.83.94', 'separate_ra': 0},
                           network='host', auto_remove=True, detach=True, name='dynamicsim')


if __name__ == "__main__":
    # ipaddress = "127.0.0.1"
    # try:
    #     opts, args = getopt.getopt(sys.argv[1:], "hi:", ["ipaddress="])
    # except getopt.GetoptError:
    #     print('CommunicationRO.py -i <ipaddress>')
    #     sys.exit(2)
    #
    # for opt, arg in opts:
    #     if opt == '-h':
    #         print('CommunicationRO.py -i <ipaddress>')
    #         sys.exit()
    #     elif opt in ("-i", "--ipaddress"):
    #         ipaddress = arg

    messagehandler = CommunicationRO()
    #messagehandler.start_simulation(1000, 5)
    messagehandler.run()

