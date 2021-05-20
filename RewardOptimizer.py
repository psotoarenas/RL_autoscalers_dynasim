import threading
import time
import x_pb2
import random
from base_logger import logger
import base_logger
from MicroserviceDataClass import MicroserviceDataClass
import TimeManagment
import numpy as np
import shortuuid

class RewardOptimizer:
    def __init__(self, timemanager):
        self.number_of_ms = 0
        self.number_of_servers = 0
        self.timemanager = timemanager
        self.total_cpu_server = 0.0
        self.total_cpu_usage = 0.0
        self.total_overflow = 0.0
        self.weight_per_ms = {}
        self.ms_removed = []
        self.ms_started = []
        self.server_started = []
        self.server_removed = []
        self.loadbalancer = "LoadBalancer"
        self.test_ms = {"MS_1": 0.5, "MS_2": 0.5, "MS_3": 0.1, "MS_4": 0.1, "MS_5": 0.1}
        self.server_dict = {}
        #RA Parameters
        self.distribution_rate = 'uniform'
        self.distribution_execution_time = 'uniform'
        self.distribution_size = 'exact'
        self.size_params = [300]
        self.job_list = [433, 348, 950, 481, 25, 896, 156, 191, 674, 261, 897, 419, 950]
        self.rate_params = [100]
        self.memory = 0
        self.execution_time_params = [1]

        self.last_report = time.time()

        self.tick_increase = 2
        self.list_ms = []

        base_logger.default_extra = {'app_name': 'RewardOptimizer', 'node': 'localhost'}
        base_logger.timemanager = self.timemanager

    def getUpdate(self):
        print('Time: ' + str((time.time() - self.last_report) * 1000) + ' ms')
        self.last_report = time.time()
        messages_ro = self.load_algorithm_test()
        messages_ra = self.getUpdateRA()
        return messages_ra + messages_ro

    def load_algorithm(self):
        #must be defined here
        messages_to_send = []
        self.ms_removed = []

        for ms in self.list_ms:
            print('Name: {}, CPU: {:.2f}, Overflow: {}, Status: {}, Server: {}'.format(ms.name, ms.cpu_usage, ms.overflow, ms.state, ms.server))

        if self.number_of_ms > 0:
            cpu_usage = self.total_cpu_usage / self.number_of_ms
            overflow = self.total_overflow / self.number_of_ms
            base_logger.info("MS: {} ({})".format(self.number_of_ms, self.timemanager.getCurrentSimulationTick()))
            base_logger.info("Cpu Usage: {:.2f}".format(cpu_usage))
            # base_logger.info("Overflow: {:.2f}".format(overflow))

            if cpu_usage < 0.4 and self.number_of_ms > 1:
                ms_name, _ = self.weight_per_ms.popitem()
                self.ms_removed.append(ms_name)
                delete_actor = self.remove_actor(ms_name, 'microservice')
                print("Deleted: {}".format(ms_name))
                messages_to_send.append(delete_actor)

            elif cpu_usage > 0.8 and len(self.ms_started) == 0:
                # actor_name = "MS_{}".format(len(self.weight_per_ms.keys()) + 1)
                actor_name = "MS_{}".format(shortuuid.ShortUUID().random(length=8))
                parameters = [1.0, 1.0, 1]
                new_actor = self.create_new_microservice(actor_name, actor_type='class_SimpleMicroservice', parameters=parameters,
                                                         incoming_actors=["LoadBalancer"], outgoing_actors=[], server=self.get_best_server())
                # print(new_actor)
                base_logger.info("New MS: {}".format(actor_name))
                self.ms_started.append(actor_name)
                messages_to_send.append(new_actor)

            # ParameterMessages = self.create_parameter_message([self.cpu])
            # toSimMessage = x_pb2.ToSimulationMessage()
            # update_weight = x_pb2.UpdateParameterActor()
            # update_weight.type = "microservice"
            # update_weight.name = "MS_1"
            # update_weight.parameter_name = "current_thread_limit"
            # update_weight.parameters.extend(ParameterMessages)
            # toSimMessage.update_parameter_actor.CopyFrom(update_weight)
            # messages_to_send.append(toSimMessage)

            self.number_of_ms = 0
            self.total_cpu_usage = 0.0
            self.total_overflow = 0.0

        if self.number_of_servers > 0:
            cpu_usage = self.total_cpu_server / self.number_of_servers
            # base_logger.info("Servers: {}".format(self.number_of_servers))
            # base_logger.info("Cpu Usage server: {:.2f}".format(cpu_usage))
            # base_logger.info("Overflow: {:.2f}".format(overflow))

            if cpu_usage < 0.1 and self.number_of_ms > 1:
                ms_name, _ = self.weight_per_ms.popitem()
                self.ms_removed.append(ms_name)
                delete_actor = self.remove_actor(ms_name, 'microservice')
                # print(delete_actor)
                #messages_to_send.append(delete_actor)

            elif cpu_usage > 0.9 and len(self.server_started) == 0:
                actor_name = "Server_{}".format(len(self.server_dict) + 1)
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

                # print(new_actor)
                self.server_started.append(actor_name)
                messages_to_send.append(toSimMessage)
                print("Create new Server: {}".format(actor_name))
            # ParameterMessages = self.create_parameter_message([self.cpu])
            # toSimMessage = x_pb2.ToSimulationMessage()
            # update_weight = x_pb2.UpdateParameterActor()
            # update_weight.type = "microservice"
            # update_weight.name = "MS_1"
            # update_weight.parameter_name = "current_thread_limit"
            # update_weight.parameters.extend(ParameterMessages)
            # toSimMessage.update_parameter_actor.CopyFrom(update_weight)
            # messages_to_send.append(toSimMessage)

            self.number_of_servers = 0
            self.total_cpu_server = 0.0

        return messages_to_send

    def load_algorithm_test(self):
        messages_to_send = []

        for ms in self.list_ms:
            print('Name: {}, CPU: {:.2f}, Overflow: {}, Status: {}, Server: {}'.format(ms.name, ms.cpu_usage, ms.overflow, ms.state, ms.server))

        shutdown_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'SHUTDOWN']

        for ms in shutdown_ms:
            self.list_ms.remove(ms)

        active_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'RUNNING']
        booting_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'BOOTING']
        all_ms = [x for x in self.list_ms if 'MS' in x.name]

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
                                                         incoming_actors=["LoadBalancer"], outgoing_actors=[], server=self.get_best_server())
                # print(new_actor)
                base_logger.info("New MS: {}".format(actor_name))
                messages_to_send.append(new_actor)

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
        cpu_max = 100
        server_to_select = ''
        for server, cpu in self.server_dict.items():
            if cpu < cpu_max:
                server_to_select = server
                cpu_max = cpu
        return server_to_select

    def add_counter(self, counter):
        new_ms = None
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
        if counter.metric == 'service_list':
            ms_server = counter.value.split(',')
            for ms_name in ms_server:
                if not contains(self.list_ms, lambda x: x.name == counter.actor_name):
                    ms = MicroserviceDataClass(ms_name)
                    self.list_ms.append(new_ms)
                else:
                    ms = [x for x in self.list_ms if x.name == ms_name][0]
                ms.server = counter.actor_name

        if counter.actor_name in self.ms_removed:
            return
        
        if counter.actor_name in self.ms_started:
            self.ms_started.remove(counter.actor_name)

        if counter.actor_name in self.server_started:
            self.server_started.remove(counter.actor_name)

        if counter.actor_name not in self.weight_per_ms and "MS" in counter.actor_name:
            self.weight_per_ms[counter.actor_name] = 0.5
            print(self.weight_per_ms)

        if counter.metric == 'cpu_usage' and "MS" in counter.actor_name:
            self.number_of_ms += 1
            self.total_cpu_usage += counter.value
        elif counter.metric == 'cpu_usage' and "Server" in counter.actor_name:
            self.server_dict.update({counter.actor_name: counter.value})
            self.number_of_servers += 1
            self.total_cpu_server += counter.value
        elif counter.metric == 'overflow':
            self.total_overflow += counter.value



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
            if tick % 50 == 0:
                self.tick_increase += 1
        if tick > 1500 and self.tick_increase > 0:
            if tick % 50 == 0:
                self.tick_increase -= 1

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
