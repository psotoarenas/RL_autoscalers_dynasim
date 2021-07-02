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
# This example displays the vertical scaling option (adding more resources to a microservice)

# This example is tested with the 'server_migration' docker image of the simulator
# To use this example, change line 16 of CommunicationRO.py to self.ro_agent = RO_VerticalScaling(self.timemanager)

# Example:
## Each MS two parameters for the vertical scaling: current_thread_limit and maximum_thread_limit

## current_thread_limit: a float bigger than 0. This represents the number of threads the MS can handle at the moment.
##  If the cpu_cycles per tick is 300 and the current_thread_limit is 1.5, the MS can use 450 cpu_cycles per tick
##  This variable can be changed during the lifetime of the MS via an 'UpdateParameterActor' message

## maximum_thread_limit: a float bigger than 0. This represents the maximum number of threads the MS can handle
##  This value is constant and is set when the MS is created. When the controller sets the current_thread_limit bigger than
##  this value, the limit is maximum_thread_limit

## max_cpu_cycles_per_tick = cpu_cylces_per_tick * min(current_thread_limit, maximum_thread_limit)

# SCENARIO
## We start to go to one microservice and delete MS_dev2cM5T
## Every 10 ticks we increase the traffic generator number of jobs
## The current_thread_limit is increased when the CPU usage > 0.95 and decreased < 0.5
## The CPU usage is reported with the usage cpu cycles / cpu_cycles_per_tick (300), so the usage can be bigger than 1.0
## For this we divide it in the controller with min(current_thread_limit, maximum_thread_limit)
## The controller is only for testing this feature
## At tick 322 we increase the current_thread_limit to 4.1, but this has no effect on the load because the MS is limited to 4.0

# The command of the docker  to test this examples:
# docker run -it --rm --network host -e LENGTH=1200 -e IP_PYTHON=143.129.83.94 -e separate_ra=0 gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:counter_in_json

class RO_VerticalScaling:
    def __init__(self, timemanager):
        self.timemanager = timemanager
        self.loadbalancer = "LoadBalancer"
        # RA Parameters
        self.distribution_rate = 'uniform'
        self.distribution_execution_time = 'uniform'
        self.distribution_size = 'exact'
        self.size_params = [300]
        self.rate_params = [100]
        self.memory = 0
        self.execution_time_params = [1]

        self.tick_increase = 0
        self.list_ms = []
        self.list_server = []
        self.cpu = 1.0

        base_logger.default_extra = {'app_name': 'RewardOptimizer', 'node': 'localhost'}
        base_logger.timemanager = self.timemanager

    def getUpdate(self):
        messages_ro = self.example_algorithm()
        messages_ra = self.getUpdateRA()
        return messages_ra + messages_ro

    def example_algorithm(self):
        messages_to_send = []

        for ms in self.list_ms:
            print(
                'Name: {}, CPU: {:.2f}, Overflow: {}, Status: {}, Server: {}'.format(ms.name, ms.cpu_usage, ms.overflow,
                                                                                     ms.state, ms.server))

        shutdown_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'SHUTDOWN']

        for ms in shutdown_ms:
            self.list_ms.remove(ms)

        active_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'RUNNING']
        booting_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'BOOTING']

        for ms in self.list_ms:
            if ms.name == 'MS_dev2cM5T':
                delete_actor = self.remove_actor(ms.name, 'microservice')
                messages_to_send.append(delete_actor)

        if len(active_ms) > 0:
            cpu_usage = 0
            overflow = 0
            for ms in active_ms:
                cpu_usage += ms.cpu_usage
                overflow += ms.overflow

            cpu_usage = cpu_usage / len(active_ms) / min(self.cpu, 4.0)
            overflow = overflow / len(active_ms)
            base_logger.info("MS: {} ({})".format(len(active_ms), self.timemanager.getCurrentSimulationTick()))
            base_logger.info("Cpu Usage: {:.2f}".format(cpu_usage))
            base_logger.info("Overflow: {:.2f}".format(overflow))

            if cpu_usage < 0.5:
                self.cpu -= 0.1
                ParameterMessages = self.create_parameter_message([self.cpu])
                toSimMessage = x_pb2.ToSimulationMessage()
                update_current_thread_limit = x_pb2.UpdateParameterActor()
                update_current_thread_limit.type = "microservice"
                update_current_thread_limit.name = "MS_ji5jeVb3"
                update_current_thread_limit.parameter_name = "current_thread_limit"
                update_current_thread_limit.parameters.extend(ParameterMessages)
                toSimMessage.update_parameter_actor.CopyFrom(update_current_thread_limit)
                messages_to_send.append(toSimMessage)
                print("Current Thread limit increased to: {}".format(self.cpu))

            if cpu_usage > 0.95 and len(booting_ms) == 0:
                if self.cpu < 4.5:
                    self.cpu += 0.1
                ParameterMessages = self.create_parameter_message([self.cpu])
                toSimMessage = x_pb2.ToSimulationMessage()
                update_current_thread_limit = x_pb2.UpdateParameterActor()
                update_current_thread_limit.type = "microservice"
                update_current_thread_limit.name = "MS_ji5jeVb3"
                update_current_thread_limit.parameter_name = "current_thread_limit"
                update_current_thread_limit.parameters.extend(ParameterMessages)
                toSimMessage.update_parameter_actor.CopyFrom(update_current_thread_limit)
                messages_to_send.append(toSimMessage)
                print("Current Thread limit increased to: {}".format(self.cpu))

        for server in self.list_server:
            print('Name: {}, CPU: {:.2f}, Status: {}, MS: {}'.format(server.name, server.cpu_usage, server.state,
                                                                     [ms for ms in server.ms_list]))

        return messages_to_send

    def create_new_microservice(self, name, actor_type, incoming_actors, outgoing_actors=[], parameters=[],
                                server='Server_1'):
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

        if tick < 350:
            if tick % 10 == 0:
                self.tick_increase += 1
        if tick > 350 and self.tick_increase > 0:
            if tick % 10 == 0:
                self.tick_increase -= 1

        self.size_params[0] = 200 + 30 * self.tick_increase
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

    def run(self):
        x = threading.Thread(target=self.updateParams)
        x.start()


def contains(list, filter):
    for x in list:
        if filter(x):
            return True
    return False
