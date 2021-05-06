import threading
import time
import x_pb2
import random
from base_logger import logger
import base_logger
import TimeManagment
import numpy as np

class RewardOptimizer:
    def __init__(self, timemanager):
        self.number_of_ms = 0
        self.timemanager = timemanager
        self.total_cpu_usage = 0.0
        self.total_overflow = 0.0
        self.weight_per_ms = {}
        self.ms_removed = []
        self.ms_started = []
        self.loadbalancer = "LoadBalancer"
        self.test_ms = {"MS_1": 0.5, "MS_2": 0.5, "MS_3": 0.1, "MS_4": 0.1, "MS_5": 0.1}

        #RA Parameters
        self.distribution_rate = 'uniform'
        self.distribution_execution_time = 'uniform'
        self.distribution_size = 'exact'
        self.size_params = [300]
        self.job_list = [433, 348, 950, 481, 25, 896, 156, 191, 674, 261, 897, 419, 950]
        self.rate_params = [100]
        self.memory = 0
        self.execution_time_params = [1]

        self.cpu = 1.0
        self.last_report = time.time()

        base_logger.default_extra = {'app_name': 'RewardOptimizer', 'node': 'localhost'}
        base_logger.timemanager = self.timemanager

    def getUpdate(self):
        print('Time: ' + str((time.time() - self.last_report) * 1000) + ' ms')
        self.last_report = time.time()
        messages_ro = self.load_algorithm()
        messages_ra = self.getUpdateRA()
        return messages_ra + messages_ro

    def load_algorithm(self):
        self.ms_removed = []
        #must be defined here
        messages_to_send = []

        if self.number_of_ms > 0:
            cpu_usage = self.total_cpu_usage / self.number_of_ms
            overflow = self.total_overflow / self.number_of_ms
            base_logger.info("MS: {}".format(self.number_of_ms))
            base_logger.info("Cpu Usage: {:.2f}".format(cpu_usage))
            base_logger.info("Overflow: {:.2f}".format(overflow))

            if cpu_usage < 0.4 and self.number_of_ms > 1:
                ms_name, _ = self.weight_per_ms.popitem()
                self.ms_removed.append(ms_name)
                delete_actor = self.remove_actor(ms_name, 'microservice')
                # print(delete_actor)
                #messages_to_send.append(delete_actor)

            elif cpu_usage > 0.8 and len(self.ms_started) == 0:
                actor_name = "MS_{}".format(len(self.weight_per_ms.keys()) + 1)
                parameters = [1.0, 1.0, 0]
                new_actor = self.create_new_microservice(actor_name, actor_type='class_SimpleMicroservice', parameters=parameters,
                                                         incoming_actors=["LoadBalancer"], outgoing_actors=[])
                # print(new_actor)
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
            self.cpu += 0.1

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

    def create_new_microservice(self, name, actor_type, incoming_actors, outgoing_actors=[], parameters=[]):
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

    def remove_actor(self, name, actor='microservice'):
        toSimMessage = x_pb2.ToSimulationMessage()
        message = x_pb2.RemoveActor()
        message.type = actor
        message.name = name
        toSimMessage.remove_actor.CopyFrom(message)
        return toSimMessage

    def add_counter(self, counter):
        if counter.actor_name in self.ms_removed:
            return
        if counter.actor_name in self.ms_started:
            self.ms_started.remove(counter.actor_name)
        if counter.actor_name not in self.weight_per_ms:
            self.weight_per_ms[counter.actor_name] = 0.5
        if counter.metric == 'cpu_usage' and "MS" in counter.actor_name :
            self.number_of_ms += 1
            self.total_cpu_usage += counter.value
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

        if tick < 500:
            self.size_params[0] = 250
        elif tick < 1000:
            self.size_params[0] = 490
        elif tick < 1500:
            self.size_params[0] = 240 * 3 + 10
        elif tick < 2000:
            self.size_params[0] = 240 * 4 + 10
        elif tick < 2500:
            self.size_params[0] = 240 * 5 + 10
        elif tick < 3000:
            self.size_params[0] = 240 * 6 + 10
        elif tick < 3500:
            self.size_params[0] = 240 * 7 + 10
        elif tick < 4000:
            self.size_params[0] = 240 * 8 + 10
        elif tick < 4500:
            self.size_params[0] = 240 * 9 + 10
        elif tick < 5000:
            self.size_params[0] = 240 * 10 + 10
        elif tick < 5500:
            self.size_params[0] = 240 * 11 + 10
        elif tick < 6000:
            self.size_params[0] = 240 * 12 + 10
        elif tick < 6500:
            self.size_params[0] = 240 * 13 + 10
        elif tick < 7000:
            self.size_params[0] = 240 * 14 + 10
        elif tick < 7500:
            self.size_params[0] = 240 * 15 + 10
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