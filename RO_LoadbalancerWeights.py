import threading
import time
import x_pb2
import random
from base_logger import logger
import base_logger
from ActorDataClass import MicroserviceDataClass, ServerDataClass, LoadbalancerDataClass
import TimeManagment
import numpy as np
import shortuuid
import json

# Make sure that in the CommunicationRO.py file the handle_message function has both float and string counters (line 35-40).
# This example displays the server migration of a MS

# This example is tested with the 'server_migration' docker image of the simulator
# To use this example, change line 16 of CommunicationRO.py to self.ro_agent = RO_LoadbalancerWeight(self.timemanager)

# EXAMPLE
## Depending on certian parameters and environments, it is not preferable for the loadbalancer to equally dividing the traffic between the MS
## For example: different servers can result in different processing speeds and thus different jobs per second for each MS
## Or: when a new MS is started, the current MS have a higher load and maybe some overflow, the new MS can handle more traffic at the beginning
# to restore the load in the current MS faster

## To change the weight of a MS, a UpdateParameterActor message is sent to the simulator with reciptient the loadbalancer and parameter weight.
## The parameters are: the MS name and the new weight for this MS. For each MS a new message is sent, but these messages are automatically bundled in
# one big message by Communicator.

## A weight can be updated only with a value between 0 and 1, otherwise the weight will not be update and report a state=False back to the controller
## The loadbalancer adds all the weights and normalize them. Then, it will divide them between MS depending on the normalized weight.

## For this we need to set the algorithm of the loadbalancer in the Docker environment via: -e loadbalancer_algorithm={weighted|equal},
# default is equal, so for this the environment must not be set.

# SCENARIO
## At tick 1, 8 new MS are started to have a total MS of 10
## We generate each tick the same traffic load
## With an equal load (until tick 5) the load is divide equally between the MS, which results in a load per MS of 0.52
## Every 10 ticks we change the weight randomly for each MS, starting at tick 10.
## After 1 tick, the new weights will be printed coming from the simulator, betweem smaller than 0 or bigge than 1 will not be changed and the state will be set to False
## You will see the result in the loads of the MS which is different for each MS depending on the load.

# The command of the docker  to test this examples:
# docker run -it --rm --network host -e LENGTH=120 -e IP_PYTHON=143.129.83.94 -e separate_ra=0 -e loadbalancer_algorithm=weighted gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:new_job_passing


class RO_LoadbalancerWeight:
    def __init__(self, timemanager):
        self.timemanager = timemanager
        self.loadbalancer = None
        #RA Parameters
        self.distribution_rate = 'uniform'
        self.distribution_execution_time = 'uniform'
        self.distribution_size = 'exact'
        self.size_params = [300]
        self.rate_params = [100]
        self.memory = 0
        self.execution_time_params = [1]

        self.tick_increase = 6
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

        for ms in self.list_ms:
            print('Name: {}, CPU: {:.2f}, Overflow: {}, Status: {}, Server: {}'.format(ms.name, ms.cpu_usage, ms.overflow, ms.state, ms.server))

        shutdown_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'SHUTDOWN']

        for ms in shutdown_ms:
            self.list_ms.remove(ms)

        active_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'RUNNING']
        booting_ms = [x for x in self.list_ms if 'MS' in x.name and x.state == 'BOOTING']

        if self.loadbalancer.last_update == self.timemanager.getCurrentSimulationTick():
            for MSName, weight_state in self.loadbalancer.weights_state.items():
                print("{} last weight update state: {}, current weight: {}".format(MSName, weight_state, self.loadbalancer.weights[MSName]))

        tick = self.timemanager.getCurrentSimulationTick()
        if tick == 1:
            for i in range(8):
                actor_name = "MS_{}".format(shortuuid.ShortUUID().random(length=8))
                parameters = [1.0, 4.0, 1]
                new_actor = self.create_new_microservice(actor_name, actor_type='class_SimpleMicroservice',
                                                         parameters=parameters,
                                                         incoming_actors=[self.loadbalancer.name], outgoing_actors=[],
                                                         server=self.get_best_server())
                base_logger.info("New MS: {}".format(actor_name))
                messages_to_send.append(new_actor)

        if tick > 5 and tick % 10 == 0:
            print("Weights: ", end=' ')
            for ms in active_ms:
                weight = round(random.uniform(-.5, 1.5), 3)
                ParameterMessages = self.create_parameter_message([ms.name, weight])
                toSimMessage = x_pb2.ToSimulationMessage()
                update_weight = x_pb2.UpdateParameterActor()
                update_weight.type = "microservice"
                update_weight.name = self.loadbalancer.name
                update_weight.parameter_name = "weight"
                update_weight.parameters.extend(ParameterMessages)
                toSimMessage.update_parameter_actor.CopyFrom(update_weight)
                print("{}: {}".format(ms.name, weight), end=', ')
                messages_to_send.append(toSimMessage)
        print("\n\n")
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
        if "LoadBalancer" in counter.actor_name:
            if self.loadbalancer is None:
                self.loadbalancer = LoadbalancerDataClass(counter.actor_name)
            if counter.metric == 'weights':
                counter_json = json.loads(counter.value)
                self.loadbalancer.weights = counter_json['Weights']
                self.loadbalancer.weights_state = counter_json['Success']
                self.loadbalancer.last_update = self.timemanager.getCurrentSimulationTick()

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
        self.size_params[0] = 260 * self.tick_increase + 10
        #print(timeOfDay, new_params)
        toSimMessage = x_pb2.ToSimulationMessage()
        message = x_pb2.TrafficGeneratorParameters()
        message.name = "Client"
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
