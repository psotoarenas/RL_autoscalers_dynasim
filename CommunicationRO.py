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
            #self._communicator.set_push_socket('143.129.86.4')
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

    def start_simulation(self, total_timesteps, tick_freq=1, ip="143.129.83.94",
                         cwd="/home/ydebock/dynamicsim/mock-simulators/dynaSim/test/"):
        '''

        This function starts automatically the simulation in a non-blocking subprocess
        :param total_timesteps: total time steps that the agent will train or predict. Integer
        :param tick_freq: number of ticks that the simulator will produce an output
        :param ip: ip address from the server. It is assumed that both agent and simulation run in the same machine
        :param cwd: directory from which the make command will run
        :return:

        '''
        # here we assume that the agent and the simulator are running in the same machine
        # if using shell=True in the Popen subprocess, the command should be as single string and not list
        sim_length = total_timesteps * tick_freq
        cmd = 'ssh ydebock@143.129.83.94 \''
        cmd += "cd {};".format(cwd)
        cmd += 'make -s dynasim_run CMD_LINE_OPT="--batch --ip {} --length {} --ticks_per_second {} --report_time {}"'.format(ip,
                                                                                                                     sim_length, 1,
                                                                                                                     tick_freq)
        cmd += '\''

        process = subprocess.Popen(cmd,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   universal_newlines=True,
                                   shell=True,
                                   cwd=cwd)


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

