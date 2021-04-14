import numpy as np
import base_logger
import random
import x_pb2
from TimeManagment import TimeManagement
from Communicator import Communicator
import subprocess
import threading
import os
import signal
import time


class DynaSim:
    def __init__(self, ):
        # communicator side
        self._communicator = Communicator(5556, 5557)
        self._communicator.add_notifier(lambda m: self.handle_message(m))
        self.timemanager = TimeManagement()
        self.ro_pid = ""
        self.report_ready = threading.Event()
        self.first_observation = False
        self.process = ""

        # From MS handling
        self.number_of_ms = 0
        self.total_cpu_usage = 0.0
        self.total_overflow = 0.0
        self.max_peak_latency = 0.0
        self.avg_latency = 0.0
        self.ms_id = 3
        self.weight_per_ms = {}
        self.ms_removed = []
        self.ms_started = []
        self.messages_to_send = []
        base_logger.default_extra = {'app_name': 'EnvironmentCommunicator', 'node': 'localhost'}
        base_logger.timemanager = self.timemanager

        # Traffic Parameters
        self.distribution_rate = 'uniform'
        self.distribution_execution_time = 'uniform'
        self.distribution_size = 'exact'
        self.size_params = [300]
        self.rate_params = [100]
        self.memory = 0
        self.tick = 0
        random.seed(7)
        self.execution_time_params = [1]

    def run(self):
        with self._communicator:
            self._communicator.run()

    def handle_message(self, message: x_pb2.ToPythonMessage):
        # handle an incoming message
        self.timemanager.updateTime(message.tick_offset)
        if message.HasField("info"):
            self._communicator.set_push_socket(message.info.ipaddress)
            self.timemanager.initializeTime(message.info.tick_length)

        if message.HasField("register_communicator"):
            self.ro_pid = message.register_communicator.pid

        if message.HasField("counters"):
            # clean previous reports, we are only interested in the most recent report, clean all expected metrics
            self.number_of_ms = 0
            self.total_cpu_usage = 0.0
            self.total_overflow = 0.0
            self.max_peak_latency = 0.0
            self.avg_latency = 0.0

            # get report per microservice
            for counter in message.counters.counters_float:
                self.add_counter(counter)
            self.report_ready.set()
            self.first_observation = True  # not changed anywhere else in the code

            # simulator will wait until the agent sends a message!

    def send_messages(self, messages):
        # sends a message to the simulator
        if self.ro_pid != '':
            if messages is not None:
                for message_sim in messages:
                    self._communicator.add_message(message_sim, self.ro_pid)
            self.report_ready.clear()
            self._communicator.send()
        self.messages_to_send = []

    def add_counter(self, counter):
        # receive counters and add them to average them later
        if counter.actor_name in self.ms_removed:
            return
        if counter.actor_name in self.ms_started:
            self.ms_started.remove(counter.actor_name)
        if counter.actor_name not in self.weight_per_ms:
            self.weight_per_ms[counter.actor_name] = 0.5
        if counter.metric == 'cpu_usage':
            self.number_of_ms += 1
            self.total_cpu_usage += counter.value
        elif counter.metric == 'overflow':
            self.total_overflow += counter.value
        elif counter.metric == 'peak_latency':
            self.max_peak_latency = max(counter.value, self.max_peak_latency)
        elif counter.metric == 'avg_latency':
            self.avg_latency += counter.value

    def communicate_counters(self):
        # communicate counters (from simulator to environment)
        # right now the observation is only based on cpu usage. Needs to be changed to include more metrics
        cpu_usage = 0.
        overflow = 0.
        peak_latency = 0.
        avg_latency = 0.
        if self.number_of_ms > 0:
            cpu_usage = self.total_cpu_usage / self.number_of_ms
            overflow = self.total_overflow / self.number_of_ms
            peak_latency = self.max_peak_latency
            avg_latency = self.avg_latency / self.number_of_ms
            base_logger.info("MS: {}".format(self.number_of_ms))
            base_logger.info("Cpu Usage: {:.4f}".format(cpu_usage))
            base_logger.info("Overflow: {:.4f}".format(overflow))
            base_logger.info("Peak Latency: {:.4f}".format(peak_latency))
            base_logger.info("Avg Latency: {:.4f}".format(avg_latency))
        return peak_latency

    def getUpdate(self):
        # form an updated list of messages. This includes messages from the agent
        messages_agent = self.messages_to_send
        messages_traffic = self.compute_traffic()
        # messages_traffic = []
        return messages_agent + messages_traffic

    def increase_vnf(self):
        # form the message create actor
        actor_name = "MS_{}".format(self.ms_id)
        parameters = [300, 0]
        new_actor = self.create_new_microservice(actor_name, actor_type='class_SimpleMicroservice',
                                                 parameters=parameters,
                                                 incoming_actors=["LoadBalancer"], outgoing_actors=[])
        self.ms_started.append(actor_name)
        self.messages_to_send.append(new_actor)
        self.ms_id += 1

    def decrease_vnf(self):
        # form the message remove actor
        self.ms_removed = []
        if self.number_of_ms > 1:
            ms_name, _ = self.weight_per_ms.popitem()
            self.ms_removed.append(ms_name)
            delete_actor = self.remove_actor(ms_name, 'microservice')
            self.messages_to_send.append(delete_actor)

    def create_new_microservice(self, name, actor_type, incoming_actors, outgoing_actors=[], parameters=[]):
        # auxiliary function
        ParameterMessages = self.create_parameter_message(parameters)
        toSimMessage = x_pb2.ToSimulationMessage()
        create_actor = x_pb2.CreateActor()
        message = x_pb2.CreateMicroservice()
        message.actor_type = actor_type
        message.name = name
        message.server_name = "Server_1"
        message.incoming_actors.extend(incoming_actors)
        message.outgoing_actors.extend(outgoing_actors)
        message.parameters.extend(ParameterMessages)
        create_actor.microservice.CopyFrom(message)
        toSimMessage.create_actor.CopyFrom(create_actor)
        return toSimMessage

    def create_parameter_message(self, parameters):
        # auxiliary function
        list_parameter_messages = []
        for parameter in parameters:
            param_message = x_pb2.Parameter()
            if isinstance(parameter, (float, int)):
                param_message.float_value = parameter
            else:
                param_message.string_value = parameter

            list_parameter_messages.append(param_message)

        return list_parameter_messages

    def remove_actor(self, name, actor='microservice'):
        # auxiliary function
        toSimMessage = x_pb2.ToSimulationMessage()
        message = x_pb2.RemoveActor()
        message.type = actor
        message.name = name
        toSimMessage.remove_actor.CopyFrom(message)
        return toSimMessage

    def compute_traffic(self):
        # compute the traffic that is sent to the simulator
        offset = 1616745600  # 9:00 March 25, 2021
        timeOfDay = offset + self.tick
        new_params = max(int(300.0 * (0.9 + 0.1 * np.cos(np.pi * timeOfDay / 864000.0)) *
                             (4.0 + 1.2 * np.sin(2.0 * np.pi * timeOfDay / 86400.0) -
                              0.6 * np.sin(6.0 * np.pi * timeOfDay / 86400.0) +
                              0.02 * (np.sin(503.0 * np.pi * timeOfDay / 86400.0) -
                                      np.sin(709.0 * np.pi * timeOfDay / 86400.0) * random.expovariate(1.0))) +
                             self.memory + 5.0 * random.gauss(0.0, 1.0)), 0)
        if random.random() < 1e-4:
            self.memory += 200.0 * random.expovariate(1.0)
        else:
            self.memory *= 0.99
        self.tick += 1
        self.size_params[0] = new_params
        base_logger.info("Traffic: {}".format(new_params))
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

    def start_simulation(self, sim_length, tick_freq=1, ip="127.0.0.1",
                         cwd="../dynamicsim/mock-simulators/dynaSim/test/"):
        """
        This function starts automatically the simulation in a non-blocking subprocess. Here we assume that the agent
        and the simulator are running in the same machine. A timestep is an interaction of the agent with the simulator.
        We consider an interaction as the agent sending an action and receiving the state of the simulator after
        applying the action. Therefore, the simulation length is related to the tick frequency and the number of
        timesteps.

        :param total_timesteps: total time steps that the agent will train or predict. Integer
        :param tick_freq: number of ticks per second
        :param ip: ip address from the server. It is assumed that both agent and simulation run in the same machine
        :param cwd: directory from which the make command will run
        :return:
        """
        # if using shell=True in the Popen subprocess, the command should be as single string and not list
        # The os.setsid fn attach a session id to all child subprocesses created by the simulation (erlang, wooper)
        cmd = 'make -s dynasim_run CMD_LINE_OPT="--batch --ip {} --length {} --ticks {}"'.format(ip, sim_length,
                                                                                                 tick_freq)
        self.process = subprocess.Popen(cmd,
                                        stdout=subprocess.DEVNULL,
                                        shell=True,
                                        cwd=cwd,
                                        preexec_fn=os.setsid)

        # TODO: what if the agent and the simulator are running in different machines?

    def stop_simulation(self):
        if self.process:
            # Send the SIGKILL signal to all the subprocesses with a given session id
            print(f"Killing process: {self.process.pid}")
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            self.first_observation = False
            time.sleep(10)
