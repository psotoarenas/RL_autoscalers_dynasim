import sys, getopt
import x_pb2
from Communicator import Communicator
from TimeManagment import TimeManagement
from RewardOptimizer import RewardOptimizer
from RO_VerticalScaling import RO_VerticalScaling
from RO_HorizontalScaling import RO_HorizontalScaling
from RO_ServerMigration import RO_ServerMigration
from RO_LoadbalancerWeights import RO_LoadbalancerWeight
import subprocess

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
        """
        This function starts automatically the simulation in a non-blocking subprocess. Here we assume that the agent
        and the simulator are running in the same machine. A timestep is an interaction of the agent with the simulator.
        We consider an interaction as the agent sending an action and receiving the state of the simulator after
        applying the action. Therefore, the simulation length is related to the tick frequency and the number of
        timesteps.

        :param total_timesteps: total time steps that the agent will train or predict. Integer
        :param tick_freq: number of ticks per second
        :param report_ticks: how ticks a report is generated
        :param ip: ip address from the server. It is assumed that both agent and simulation run in the same machine
        :param cwd: directory from which the make command will run
        :return:
        """
        # if using shell=True in the Popen subprocess, the command should be as single string and not list
        # The os.setsid fn attach a session id to all child subprocesses created by the simulation (erlang, wooper)
        # You can play with ticks_per_second and report_ticks,
        # if you want a report every second report_ticks = ticks_per_second
        cmd = 'docker run -it --hostname docker-desktop.localdomain -p 5557:5557 -e LENGTH=200 -e tickspersecond=1 -e IP_PYTHON=143.129.83.94 -e separate_ra=0 gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration'
        #args = shlex.split(cmd)
        print(args)
        self.process = subprocess.run(args)
        print(self.process)


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

