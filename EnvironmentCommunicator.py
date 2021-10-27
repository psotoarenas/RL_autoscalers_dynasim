import numpy as np
import base_logger
import random
import x_pb2
from TimeManagment import TimeManagement
from Communicator import Communicator
from ActorDataClass import MicroserviceDataClass, ServerDataClass
import threading
import docker
import shortuuid


class DynaSim:
    def __init__(self, mode):
        # communicator side
        self._communicator = Communicator(5556, 5557)
        self._communicator.add_notifier(lambda m: self.handle_message(m))
        self.timemanager = TimeManagement()
        self.ro_pid = ""
        self.report_ready = threading.Event()
        self.first_observation = False
        self.container = ""

        # From MS handling
        self.number_of_ms = 0
        self.total_cpu_usage = 0.0
        self.total_overflow = 0.0
        self.max_peak_latency = 0.0
        self.avg_latency = 0.0
        self.ms_id = 3
        self.weight_per_ms = {}
        self.ms_removed = []
        self.list_ms = []
        self.list_server = []
        self.active_ms = []
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
        self.execution_time_params = [1]
        self.mode = mode
        if self.mode == "train":
            self.tick = 0
            # with open('trafficTrace.csv') as f:
            #     self.job_list = [int(el) for el in f.read().split()]
        else:
            self.tick = 432000
            # with open('trafficTrace.csv') as f:
            # with open('../trafficTrace.csv') as f:
            #     self.job_list = [int(el) for el in f.read().split()]
        random.seed(7)


    def run(self):
        with self._communicator:
            self._communicator.run()

    def handle_message(self, message: x_pb2.ToPythonMessage):
        # handle an incoming message
        self.timemanager.updateTime(message.tick_offset)
        if message.HasField("info"):
            # self._communicator.set_push_socket('146.175.219.201')
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
            for counter in message.counters.counters_string:
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
        if "MS_" in counter.actor_name:
            if not contains(self.list_ms, lambda x: x.name == counter.actor_name):
                new_ms = MicroserviceDataClass(counter.actor_name)
                self.list_ms.append(new_ms)
            else:
                new_ms = [x for x in self.list_ms if x.name == counter.actor_name][0]

            if counter.metric == 'cpu_usage':
                new_ms.cpu_usage = counter.value
            if counter.metric == 'overflow':
                new_ms.overflow = counter.value
            if counter.metric == 'peak_latency':
                new_ms.peak_latency = counter.value
            if counter.metric == 'avg_latency':
                new_ms.avg_latency = counter.value
            if counter.metric == 'status':
                new_ms.state = counter.value

        if 'Server_' in counter.actor_name:
            if not contains(self.list_server, lambda x: x.name == counter.actor_name):
                new_server = ServerDataClass(counter.actor_name)
                self.list_server.append(new_server)
            else:
                new_server = [x for x in self.list_server if x.name == counter.actor_name][0]

            if counter.metric == 'cpu_usage':
                new_server.cpu_usage = counter.value
            if counter.metric == 'server_info':
                print(counter.value)
            if counter.metric == 'status':
                new_server.state = counter.value
            if counter.metric == 'service_list':
                if counter.value != '':
                    ms_server = counter.value.split(',')
                    new_server.ms_list = ms_server
                    for ms_name in ms_server:
                        if not contains(self.list_ms, lambda x: x.name == ms_name):
                            ms = MicroserviceDataClass(ms_name)
                            self.list_ms.append(ms)
                        else:
                            ms = [x for x in self.list_ms if x.name == ms_name][0]
                        ms.server = counter.actor_name
                else:
                    new_server.ms_list = []

    def communicate_counters(self):
        # communicate counters (from simulator to environment)
        # print for debugging
        # for ms in self.list_ms:
        #     print('Name: {}, CPU: {:.2f}, Overflow: {:.2f}, Peak Latency: {:.2f}, Avg Latency: {:.2f}, '
        #           'Status: {}, Server: {}'.format(ms.name, ms.cpu_usage, ms.overflow, ms.peak_latency, ms.avg_latency,
        #                                           ms.state, ms.server)
        #           )
        # filter MS with a SHUTDOWN state
        shutdown_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'SHUTDOWN']
        for ms in shutdown_ms:
            self.list_ms.remove(ms)

        # filter MS with RUNNING and BOOTING state
        active_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'RUNNING']
        booting_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'BOOTING']

        cpu_usage = 0.
        overflow = 0.
        peak_latency = 0.
        avg_latency = 0.
        if len(active_ms) > 0:
            for ms in active_ms:
                self.total_cpu_usage += ms.cpu_usage
                self.total_overflow += ms.overflow
                self.avg_latency += ms.avg_latency
                self.max_peak_latency = max(ms.peak_latency, self.max_peak_latency)

            self.number_of_ms = len(active_ms)
            cpu_usage = self.total_cpu_usage / self.number_of_ms
            overflow = self.total_overflow / self.number_of_ms
            peak_latency = self.max_peak_latency
            avg_latency = self.avg_latency / self.number_of_ms
            base_logger.info("MS: {}".format(self.number_of_ms))
            base_logger.info("Cpu Usage: {:.5f}".format(cpu_usage))
            base_logger.info("Overflow: {:.5f}".format(overflow))
            base_logger.info("Peak Latency: {:.5f}".format(peak_latency))
            base_logger.info("Avg Latency: {:.5f}".format(avg_latency))
        #     todo: what to do with the booting_ms list?

        # todo: # manage server
        # for server in self.list_server:
        #     print('Name: {}, CPU: {:.2f}, Status: {}, MS: {}'.format(server.name, server.cpu_usage, server.state,
        #                                                              [ms for ms in server.ms_list]))
        #
        # for server in self.list_server:
        #     if server.state == 'SHUTDOWN':
        #         self.list_server.remove(server)
        #
        # if len(self.list_server) > 0:
        #     cpu_usage = 0
        #
        #     for server in self.list_server:
        #         cpu_usage += server.cpu_usage
        #
        #     cpu_usage = cpu_usage / len(self.list_server)
        #     # base_logger.info("Cpu Usage server: {:.2f}".format(cpu_usage))
        #     # base_logger.info("Overflow: {:.2f}".format(overflow))
        #
        #     # if cpu_usage < 0.1 and self.number_of_ms > 1:
        #     #     ms_name, _ = self.weight_per_ms.popitem()
        #     #     self.ms_removed.append(ms_name)
        #     #     delete_actor = self.remove_actor(ms_name, 'microservice')
        #     #     # print(delete_actor)
        #     #     # messages_to_send.append(delete_actor)
        #
        #     if cpu_usage > 0.8:
        #         actor_name = "Server_{}".format(shortuuid.ShortUUID().random(length=8))
        #         parameters = [300, 10, 16000]
        #
        #         ParameterMessages = self.create_parameter_message(parameters)
        #         toSimMessage = x_pb2.ToSimulationMessage()
        #         create_actor = x_pb2.CreateActor()
        #         message = x_pb2.CreateGenericActor()
        #         message.actor_type = 'class_Server'
        #         message.name = actor_name
        #         message.parameters.extend(ParameterMessages)
        #         create_actor.generic_actor.CopyFrom(message)
        #         toSimMessage.create_actor.CopyFrom(create_actor)
        #
        #         # print(new_actor)
        #         messages_to_send.append(toSimMessage)
        #         print("Create new Server: {}".format(actor_name))
        return cpu_usage, peak_latency, overflow, self.number_of_ms

    def getUpdate(self):
        # form an updated list of messages. This includes messages from the agent
        messages_agent = self.messages_to_send
        messages_traffic = self.compute_traffic()
        # messages_traffic = []
        return messages_agent + messages_traffic

    def increase_vnf(self):
        # form the message create actor
        actor_name = "MS_{}".format(shortuuid.ShortUUID().random(length=8))
        parameters = [1.0, 1.0, 1]  # num_current_threads(CPU consumption per cycle), limit_of_threads, boot_time
        new_actor = self.create_new_microservice(actor_name, actor_type='class_SimpleMicroservice',
                                                 parameters=parameters, incoming_actors=["LoadBalancer"],
                                                 outgoing_actors=[], server="Server_1")
        self.messages_to_send.append(new_actor)

    def decrease_vnf(self):
        # form the message remove actor
        active_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'RUNNING']
        if self.number_of_ms > 1:
            ms_to_delete = active_ms.pop()
            delete_actor = self.remove_actor(ms_to_delete.name, 'microservice')
            # print("Deleted: {}".format(ms_to_delete.name))
            self.messages_to_send.append(delete_actor)

    def create_new_microservice(self, name, actor_type, incoming_actors, outgoing_actors=[], parameters=[],
                                server='Server_1'):
        # auxiliary function
        ParameterMessages = self.create_parameter_message(parameters)
        toSimMessage = x_pb2.ToSimulationMessage()
        create_actor = x_pb2.CreateActor()
        message = x_pb2.CreateMicroservice()
        message.actor_type = actor_type
        message.name = name
        message.server_name = server
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
        # add if it is necessary to repeat the same trace.
        if self.mode == "train" and self.tick == 86399:
            self.tick = 0
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

    def start_simulation(self, sim_length, tick_freq=1, report_ticks=5, ip="127.0.0.1"):
        """
        This function starts automatically the simulation in a non-blocking subprocess. Here we assume that the agent
        and the simulator are running in the same machine. A timestep is an interaction of the agent with the simulator.
        We consider an interaction as the agent sending an action and receiving the state of the simulator after
        applying the action. Therefore, the simulation length is related to the tick frequency and the number of
        timesteps.

        :param sim_length: total time steps that the agent will train or predict. Integer
        :param tick_freq: number of ticks per second
        :param report_ticks: how ticks a report is generated
        :param ip: ip address from the server. It is assumed that both agent and simulation run in the same machine
        :return:
        """
        # You can play with ticks_per_second and report_ticks,
        # if you want a report every second report_ticks = ticks_per_second

        # Docker container runs with command:
        # docker run -it --rm -p 5556:5556 -h docker-simulation.localdomain -e LENGTH=sim_length -e tickspersecond=tick_freq -e IP_PYTHON=ip -e separate_ra=0 gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration

        print("Starting simulation")
        environment = ["LENGTH={}".format(sim_length),
                       "tickspersecond={}".format(tick_freq),
                       "IP_PYTHON={}".format(ip),
                       "reportticks={}".format(report_ticks),
                       "separate_ra=0"]
        client_local = docker.from_env()   # connects to docker daemon
        base_url = "ssh://darpa@{}".format(ip)
        # client_remote = docker.DockerClient(base_url=base_url, use_ssh_client=False)

        client = client_local

        self.container = client.containers.run(
            image="gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration",
            environment=environment,
            # network='host',
            hostname="docker-simulation.localdomain",
            ports={'5556/tcp': 5556},
            auto_remove=False,
            detach=True,
            name="dynasim",
            stdin_open=True,
            tty=True,
        )  # if detach=True, the command returns a container object


    def stop_simulation(self):
        if self.container:
            # stop the docker container
            self.container.stop()  # default time for stopping: 10 secs
            # self.container.remove()
            self.first_observation = False
            self.tick = 0
            self.list_ms = []
            # time.sleep(20)
            existing_container = True
            print("Container stopped")
        else:
            existing_container = False
            print("No container to stop")

        return existing_container

    def restart_simulation(self):
        print("Restarting simulation")
        if self.container:
            # restart the docker container
            self.container.restart()  # default time for stopping: 10 secs
            self.first_observation = False
            # self.tick = 0
            self.list_ms = []
            # time.sleep(15)
            existing_container = True
            print("Container restarted")
        else:
            existing_container = False
            print("No container to restart")

        return existing_container


def contains(list_ms, filter_ms):
    for x in list_ms:
        if filter_ms(x):
            return True
    return False
