import threading
import time
import x_pb2
import random
from base_logger import logger
import base_logger
from ActorDataClass import MicroserviceDataClass, ServerDataClass
import TimeManagment
import numpy as np
import shortuuid
import json

# Make sure that in the CommunicationRO.py file the handle_message function has both float and string counters (line 35-40).
# This example displays the horizontal scaling option (adding more servers to host microservices)

# This example is tested with the 'server_migration' docker image of the simulator
# To use this example, change line 16 of CommunicationRO.py to self.ro_agent = RO_HorizontalScaling(self.timemanager)

# EXAMPLE
## Each server has a limited amount of resources (in this case CPU resources). To deploy more microservices, we need start a new server.
## Each server has three parameters: cpu_cylces_per_second, number of cores, memory capacity(MB).
## For example: [300, 10, 16000] ==> In this example the server can process 3000 cpu_cycles per second
## To create a new server, we use the default message (GenericActor) to start an actor (lines 137-145)
## The parameters for the server are created via the 'create_parameter_message' function, which are passed to the server actor



# SCENARIO
## The initial server which start with the simulator has the following paramters: [300, 40, 16000]
## This server will take longer to reach the load of 0.8, before starting a new server
## Every 10 ticks we increase the number of jobs for traffic generator with the right to create a new MS
## When the cpu usage of the server is bigger than 0.8 we start a new server.
## After 600 ticks the load is decreased every 10 ticks.
## When the cpu usage of the server is smaller than 0.5 we delete the last created server and the remaining microservices on it.
## The controller is only for testing this feature

# The command of the docker  to test this examples:
# docker run -it --rm --network host -e LENGTH=1200 -e IP_PYTHON=143.129.83.94 -e separate_ra=0 gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:new_job_passing

class RO_HorizontalScaling:
    def __init__(self, timemanager):
        self.timemanager = timemanager
        self.loadbalancer = "LoadBalancer"
        #RA Parameters
        self.distribution_rate = 'uniform'
        self.distribution_execution_time = 'uniform'
        self.distribution_size = 'exact'
        self.size_params = [300]
        self.rate_params = [100]
        self.memory = 0
        self.execution_time_params = [1]

        self.tick_increase = 2
        self.list_ms = []
        self.list_server = []

        base_logger.default_extra = {'app_name': 'RewardOptimizer', 'node': 'localhost'}
        base_logger.timemanager = self.timemanager

    def getUpdate(self):
        messages_ro_ms = self.example_algorithm_ms()
        messages_ro_server = self.example_algorithm_server()
        messages_ra = self.getUpdateRA()
        return messages_ra + messages_ro_ms + messages_ro_server

    def example_algorithm_ms(self):
        print()
        messages_to_send = []

        # for ms in self.list_ms:
        #     print('Name: {}, CPU: {:.2f}, Overflow: {}, Status: {}, Server: {}'.format(ms.name, ms.cpu_usage, ms.overflow, ms.state, ms.server))

        shutdown_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'SHUTDOWN']

        for ms in shutdown_ms:
            self.list_ms.remove(ms)

        active_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'RUNNING']
        booting_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'BOOTING']

        if len(active_ms) > 0:
            cpu_usage = 0
            overflow = 0
            for ms in active_ms:
                cpu_usage += ms.cpu_usage
                overflow += ms.overflow

            cpu_usage = cpu_usage / len(active_ms)
            overflow = overflow / len(active_ms)
            base_logger.info("MS: {} ({})".format(len(active_ms), self.timemanager.getCurrentSimulationTick()))
            base_logger.info("Cpu Usage: {:.2f}".format(cpu_usage))
            base_logger.info("Overflow: {:.2f}".format(overflow))

            if cpu_usage < 0.4 and len(active_ms) > 1:
                ms_to_delete = active_ms.pop()
                delete_actor = self.remove_actor(ms_to_delete.name, 'microservice')
                print("Deleted: {}".format(ms_to_delete.name))
                messages_to_send.append(delete_actor)

            elif cpu_usage > 0.8 and len(booting_ms) == 0:
                actor_name = "MS_{}".format(shortuuid.ShortUUID().random(length=8))
                parameters = [1.0, 4.0, 1]
                new_actor = self.create_new_microservice(actor_name, actor_type='class_SimpleMicroservice', parameters=parameters,
                                                         incoming_actors=[self.loadbalancer], outgoing_actors=[], server=self.get_best_server())
                base_logger.info("New MS: {}".format(actor_name))
                messages_to_send.append(new_actor)

        return messages_to_send

    def example_algorithm_server(self):
        print()
        messages_to_send = []

        for server in self.list_server:
            print('Name: {}, CPU: {:.2f}, Status: {}, MS: {}'.format(server.name, server.cpu_usage, server.state, [ms for ms in server.ms_list]))

        for server in self.list_server:
            if server.state == 'SHUTDOWN':
                self.list_server.remove(server)

        active_servers = [x for x in self.list_server if x.state == 'RUNNING']

        if len(active_servers) > 0:
            cpu_usage = 0

            for server in active_servers:
                cpu_usage += server.cpu_usage

            cpu_usage = cpu_usage / len(active_servers)
            base_logger.info("Cpu Usage server: {:.2f}".format(cpu_usage))

            if cpu_usage < 0.4 and len(active_servers) > 1:
                server_to_delete = active_servers.pop()
                delete_actor = self.remove_actor(server_to_delete.name, 'server')
                print("Deleted: {}".format(server_to_delete.name))
                messages_to_send.append(delete_actor)

            if cpu_usage > 0.8:
                actor_name = "Server_{}".format(shortuuid.ShortUUID().random(length=8))
                parameters = [300, 10, 16000]

                ParameterMessages = self.create_parameter_message(parameters)
                toSimMessage = x_pb2.ToSimulationMessage()
                create_actor = x_pb2.CreateActor()
                message = x_pb2.CreateGenericActor()
                message.actor_type = 'class_Server'
                message.name = actor_name
                message.parameters.extend(ParameterMessages)
                create_actor.generic_actor.CopyFrom(message)
                toSimMessage.create_actor.CopyFrom(create_actor)
                messages_to_send.append(toSimMessage)
                print("Create new Server: {}".format(actor_name))

        return messages_to_send

    def create_new_microservice(self, name, actor_type, incoming_actors, outgoing_actors=[], parameters=[], server='Server_1'):
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

    def remove_actor(self, name, actor='microservice'):
        toSimMessage = x_pb2.ToSimulationMessage()
        message = x_pb2.RemoveActor()
        message.type = actor
        message.name = name
        toSimMessage.remove_actor.CopyFrom(message)
        return toSimMessage

    def get_best_server(self):
        cpu_max = 1
        server_to_select = ''
        for server in self.list_server:
            if server.cpu_usage < cpu_max and server.state == 'RUNNING':
                server_to_select = server.name
                cpu_max = server.cpu_usage
        return server_to_select

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
                    ms_server = json.loads(counter.value)
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

    def create_parameter_message(self, parameters):
        list_parameter_messages = []
        for parameter in parameters:
            param_message = x_pb2.Parameter()
            if isinstance(parameter, (float, int)):
                param_message.float_value = parameter
            else:
                param_message.string_value = parameter

            list_parameter_messages.append(param_message)

        return list_parameter_messages

    def updateParams(self):
        while True:
            time.sleep(0.5)

    def getUpdateRA(self):
        tick = self.timemanager.getCurrentSimulationTick()

        if tick < 600:
            if tick % 10 == 0:
                self.tick_increase += 1
        if tick > 600 and self.tick_increase > 0:
            if tick % 10 == 0:
                self.tick_increase -= 1

        self.size_params[0] = 260 * self.tick_increase + 10
        toSimMessage = x_pb2.ToSimulationMessage()
        message = x_pb2.TrafficGeneratorParameters()
        message.distribution_rate = self.distribution_rate
        message.parameters_rate.extend(self.rate_params)
        message.name = "Client"

        message.distribution_execution_time = self.distribution_execution_time
        message.parameters_execution_time.extend(self.execution_time_params)

        message.distribution_size = self.distribution_size
        message.parameters_size.extend(self.size_params)
        toSimMessage.traffic_generator_params.CopyFrom(message)
        return [toSimMessage]

    def run(self):
        x = threading.Thread(target=self.updateParams)
        x.start()


def contains(list_actors, filter_name):
    for x in list_actors:
        if filter_name(x):
            return True
    return False
