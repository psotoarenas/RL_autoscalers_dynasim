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
# This example displays the server migration of a MS

# This example is tested with the 'server_migration' docker image of the simulator
# To use this example, change line 16 of CommunicationRO.py to self.ro_agent = RO_ServerMigration(self.timemanager)

# EXAMPLE
## Sometimes it is needed to move a MS from one server to another server.
## For example: when two or more MS communicate constantly, they can be better placed on one server,
## Or, when scaling down in MS, the MS on two server can be combined on one server to shutdown a server

## To migrate a MS, a UpdateParameterActor message is sent to the simulator with reciptient the server running the MS and parameter migrate_service
## The parameters are: the MS name and the server name where the MS should migrate to.
## For now the MS keeps it jobs and is directly migrated to the new server


# SCENARIO
## A second server is created at tick 5.
## Every 10 ticks the traffic increased so a new MS must be created (no vertical scaling) to handle the traffic
## The new MS is automatically placed on Server_1 (the first server)
## At tick 95 all the active MS (state = RUNNING) are migrated to the new server created at tick 5.
## after this you will see in the prints that the MS are migrated to the new server
## The new MS after 95 will still be placed on Server_1 and the loadbalancer will also stay at Server_1

# The command of the docker  to test this examples:
# docker run -it --rm --network host -e LENGTH=120 -e IP_PYTHON=143.129.83.94 -e separate_ra=0 gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:counter_in_json


class RO_ServerMigration:
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

        self.last_report = time.time()

        self.tick_increase = 2
        self.list_ms = []
        self.list_server = []

        base_logger.default_extra = {'app_name': 'RewardOptimizer', 'node': 'localhost'}
        base_logger.timemanager = self.timemanager

    def getUpdate(self):
        messages_ro = self.example_algorithm()
        messages_ra = self.getUpdateRA()
        return messages_ra + messages_ro



    def example_algorithm(self):
        messages_to_send = []

        # for ms in self.list_ms:
        #     print('Name: {}, CPU: {:.2f}, Overflow: {}, Status: {}, Server: {}'.format(ms.name, ms.cpu_usage, ms.overflow, ms.state, ms.server))

        shutdown_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'SHUTDOWN']

        for ms in shutdown_ms:
            self.list_ms.remove(ms)

        active_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'RUNNING']
        booting_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'BOOTING']

        if self.timemanager.getCurrentSimulationTick() == 5:
            actor_name = "Server_{}".format(shortuuid.ShortUUID().random(length=8))
            parameters = [300, 40, 16000]
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

        if self.timemanager.getCurrentSimulationTick() == 95:
            for ms in active_ms:
                ParameterMessages = self.create_parameter_message([ms.name, self.get_best_server()])
                toSimMessage = x_pb2.ToSimulationMessage()
                migrate_service = x_pb2.UpdateParameterActor()
                migrate_service.type = "server"
                migrate_service.name = "Server_1"
                migrate_service.parameter_name = "migrate_service"
                migrate_service.parameters.extend(ParameterMessages)
                toSimMessage.update_parameter_actor.CopyFrom(migrate_service)
                messages_to_send.append(toSimMessage)

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
                # actor_name = "MS_{}".format(len(all_ms) + 1)
                actor_name = "MS_{}".format(shortuuid.ShortUUID().random(length=8))
                parameters = [1.0, 1.0, 1]
                new_actor = self.create_new_microservice(actor_name, actor_type='class_SimpleMicroservice', parameters=parameters,
                                                         incoming_actors=["LoadBalancer"], outgoing_actors=[], server="Server_1")
                # print(new_actor)
                base_logger.info("New MS: {}".format(actor_name))
                messages_to_send.append(new_actor)

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

        return messages_to_send

    def weight_test(self):
        random_ms = {}
        messages_to_send = []
        i = 1
        for ms in range(5):
            weight = round(max(0.1, float(random.randint(-10, 100))/100), 3)
            name = 'MS_{}'.format(i)
            i += 1
            random_ms[name] = weight
        print("Prev list: " + str(self.test_ms))
        for (name, weight) in self.test_ms.items():
            if weight == 0 and random_ms.get(name) != 0:
                parameters = [300, 0]
                new_actor = self.create_new_microservice(name, actor_type='class_SimpleMicroservice', parameters=parameters,
                                                         incoming_actors=["LoadBalancer"], outgoing_actors=[])
                messages_to_send.append(new_actor)

                ParameterMessages = self.create_parameter_message([name, weight])
                toSimMessage = x_pb2.ToSimulationMessage()
                update_weight = x_pb2.UpdateParameterActor()
                update_weight.type = "microservice"
                update_weight.name = "LoadBalancer"
                update_weight.parameter_name = "weight"
                update_weight.parameters.extend(ParameterMessages)
                toSimMessage.update_parameter_actor.CopyFrom(update_weight)

                messages_to_send.append(toSimMessage)

                print("actor created")

            elif weight != 0 and random_ms.get(name) == 0:
                delete_actor = self.remove_actor(name, 'microservice')
                messages_to_send.append(delete_actor)
                print("actor deleted")

            elif weight != 0 and random_ms.get(name) != 0:
                ParameterMessages = self.create_parameter_message([name, weight])
                toSimMessage = x_pb2.ToSimulationMessage()
                update_weight = x_pb2.UpdateParameterActor()
                update_weight.type = "microservice"
                update_weight.name = "LoadBalancer"
                update_weight.parameter_name = "weight"
                update_weight.parameters.extend(ParameterMessages)
                toSimMessage.update_parameter_actor.CopyFrom(update_weight)
                messages_to_send.append(toSimMessage)

        print("New list: " + str(random_ms), end='\n\n')

        self.test_ms = random_ms
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
        # timeOfDay = self.timemanager.getCurrentSimulationTime()
        # new_params = max(int(300.0 * (0.9 + 0.1 * np.cos(np.pi * timeOfDay / 864000.0)) * (
        #             4.0 + 1.2 * np.sin(2.0 * np.pi * timeOfDay / 86400.0) - 0.6 * np.sin(
        #         6.0 * np.pi * timeOfDay / 86400.0) + 0.02 * (np.sin(503.0 * np.pi * timeOfDay / 86400.0) - np.sin(
        #         709.0 * np.pi * timeOfDay / 86400.0) * random.expovariate(1.0))) + self.memory + 5.0 * random.gauss(
        #     0.0, 1.0)), 0)
        # if random.random() < 1e-4:
        #     self.memory += 200.0 * random.expovariate(1.0)
        # else:
        #     self.memory *= 0.99

        tick = self.timemanager.getCurrentSimulationTick()

        if tick < 1500:
            if tick % 10 == 0:
                self.tick_increase += 1

        self.size_params[0] = 260 * self.tick_increase + 10
        #print(timeOfDay, new_params)
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
