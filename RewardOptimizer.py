import threading
import time
import x_pb2
import random
import TimeManagment


class RewardOptimizer:
    def __init__(self, timemanager):
        self.number_of_ms = 0
        self.timemanager = timemanager
        self.total_cpu_usage = 0.0
        self.total_overflow = 0.0
        self.max_peak_latency = 0.0
        self.weight_per_ms = {}
        self.ms_removed = []
        self.ms_started = []
        self.test_ms = {"MS_1": 0.5, "MS_2": 0.5, "MS_3": 0.0, "MS_4": 0.0, "MS_5": 0.0}
        self.oldlatency = 0.0
        with open('PIcontroller.csv') as f:
            f.readline()
            line = f.readline()[:-1].split(sep=',')
            self.tgtlatency = float(line[0])
            self.alpha = float(line[1])
            self.beta = float(line[2])
            self.soft = int(line[3])
        #self.tgtlatency = 0.02
        #self.alpha = 0.1 # default 80.0
        #self.beta = 100.0 # default 40.0
        #self.soft = 1
        self.fraction = 0.0 
        #self.counter = 0

    def getUpdate(self):
        return self.load_algorithm()
        #return self.weight_test()

    def load_algorithm(self):
        self.ms_removed = []
        if self.number_of_ms > 0:
            cpu_usage = self.total_cpu_usage / self.number_of_ms
            overflow = self.total_overflow / self.number_of_ms
            latency = self.max_peak_latency
            print("MS: {}".format(self.number_of_ms), end=', ')
            print("Cpu Usage: {:.4f}".format(cpu_usage), end=', ')
            print("Overflow: {:.4f}".format(overflow), end=', ')
            print("Latency: {:.4f}".format(latency), end=', ')

            messages_to_send = []

            alpha = self.alpha
            beta = self.beta
            tgt = self.tgtlatency 
            old = self.oldlatency
            fraction = self.fraction
            delta = alpha * (latency - tgt) + beta * (latency - old)
            if self.soft==1 and self.number_of_ms>1: delta += fraction
            else: fraction = 0.0

            print("delta: {:.4f}".format(delta), end=', ')
            print("fraction: {:.4f}".format(fraction), end=', ')
            print('#swpms', self.weight_per_ms, end=', ')
            if self.number_of_ms != len(self.weight_per_ms):
                print('PANIC', end=', ')

            if delta < -1.0 and self.number_of_ms > 1:
                ms_name, _ = self.weight_per_ms.popitem()
                self.ms_removed.append(ms_name)
                delete_actor = self.remove_actor(ms_name, 'microservice')
                #print(delete_actor)
                print("Action: -1")
                self.fraction = delta + 1.0
                messages_to_send.append(delete_actor)

            elif delta > 1.0 and len(self.ms_started) == 0:
                actor_name = "MS_{}".format(len(self.weight_per_ms.keys()) + 1)
                parameters = [1.0, 1.0, 2]
                new_actor = self.create_new_microservice(actor_name, actor_type='class_SimpleMicroservice',
                                                         parameters=parameters,
                                                         incoming_actors=["LoadBalancer"], outgoing_actors=[])

                self.ms_started.append(actor_name)
                print("Action: +1")
                self.fraction = delta - 1.0
                messages_to_send.append(new_actor)

            else:
                print("Action: 0")
                self.fraction = delta

            #print("delta: {:.4f}".format(delta), end=', ')
            #print("fraction: {:.4f}".format(self.fraction))

            self.number_of_ms = 0
            self.total_cpu_usage = 0.0
            self.total_overflow = 0.0
            self.max_peak_latency = 0.0
            self.oldlatency = latency

            #self.counter += 1
            #if self.counter%86400==0:
            #    self.beta+=10.0
            #    print("beta update:", self.beta)
            #else: print("no update")

            return messages_to_send

    def weight_test(self):
        random_ms = {}
        messages_to_send = []
        i = 1
        for ms in range(5):
            weight = round(max(0.0, float(random.randint(-5, 10)) / 10), 3)
            name = 'MS_{}'.format(i)
            i += 1
            random_ms[name] = weight
        print("Prev list: " + str(self.test_ms))
        for (name, weight) in self.test_ms.items():
            if weight == 0 and random_ms.get(name) != 0:
                parameters = [1.0, 1.0, 0]
                new_actor = self.create_new_microservice(name, actor_type='class_SimpleMicroservice',
                                                         parameters=parameters,
                                                         incoming_actors=["LoadBalancer"], outgoing_actors=[])

                messages_to_send.append(new_actor)
                print("actor created")

            elif weight != 0 and random_ms.get(name) == 0:
                delete_actor = self.remove_actor(name, 'microservice')
                messages_to_send.append(delete_actor)
                print("actor deleted")

            elif weight != 0 and random_ms.get(name) == 0:
                toSimMessage = x_pb2.ToSimulationMessage()
                update_weight = x_pb2.UpdateParameterActor()
                update_weight.type = "microservice"
                update_weight.name = name
                update_weight.parameter_name = "weight"
                update_weight.value = weight
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
        if counter.actor_name not in self.weight_per_ms and counter.actor_name not in self.ms_removed and "MS" in counter.actor_name:
            self.weight_per_ms[counter.actor_name] = 0.5
#        if counter.actor_name not in self.weight_per_ms:
#            self.weight_per_ms[counter.actor_name] = 0.5
        if counter.actor_name in self.ms_started:
            self.ms_started.remove(counter.actor_name)
        if counter.metric == 'cpu_usage' and "MS" in counter.actor_name:
            self.number_of_ms += 1
            self.total_cpu_usage += counter.value
        elif counter.metric == 'overflow':
            self.total_overflow += counter.value
        elif counter.metric == 'peak_latency':
            self.max_peak_latency = max(counter.value, self.max_peak_latency)

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

    def run(self):
        x = threading.Thread(target=self.updateParams)
        x.start()
