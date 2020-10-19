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
        self.weight_per_ms = {}
        self.ms_removed = []
        self.test_ms = {"MS_1": 0.5, "MS_2": 0.5, "MS_3": 0.0, "MS_4": 0.0, "MS_5": 0.0}

    def getUpdate(self):
        return self.load_algorithm()
        #return self.weight_test()

    def load_algorithm(self):
        self.ms_removed = []
        if self.number_of_ms > 0:
            cpu_usage = self.total_cpu_usage / self.number_of_ms
            overflow = self.total_overflow / self.number_of_ms
            print("#MS: {}".format(self.number_of_ms), end=', ')
            print("Cpu Usage: {:.2f}".format(cpu_usage), end=', ')
            print("Overflow: {:.2f}".format(overflow))

            messages_to_send = []

            if cpu_usage < 0.5 and self.number_of_ms > 1:
                ms_name, _ = self.weight_per_ms.popitem()
                self.ms_removed.append(ms_name)
                delete_actor = self.remove_actor(ms_name, 'microservice')
                print(delete_actor)
                messages_to_send.append(delete_actor)

            elif cpu_usage > 0.8:
                actor_name = "MS_{}".format(len(self.weight_per_ms.keys()) + 1)
                parameters = [300, round(random.random(), 2)]
                new_actor = self.create_new_actor(actor_name, actor='microservice', parameters=parameters)
                print(new_actor)
                messages_to_send.append(new_actor)

            self.number_of_ms = 0
            self.total_cpu_usage = 0.0
            self.total_overflow = 0.0

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
                parameters = [100, random_ms.get(name)]
                new_actor = self.create_new_actor(name, actor='microservice', parameters=parameters)
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

    def create_new_actor(self, name, actor='microservice', parameters=[]):
        toSimMessage = x_pb2.ToSimulationMessage()
        create_actors = x_pb2.CreateActors()
        message = x_pb2.CreateActor()
        message.type = actor
        message.name = name
        message.parameters.extend(parameters)
        create_actors.create_actors.add().CopyFrom(message)
        toSimMessage.create_actors.CopyFrom(create_actors)
        return toSimMessage

    def remove_actor(self, name, actor='microservice'):
        toSimMessage = x_pb2.ToSimulationMessage()
        remove_actors = x_pb2.RemoveActors()
        message = x_pb2.RemoveActor()
        message.type = actor
        message.name = name
        remove_actors.remove_actors.add().CopyFrom(message)
        toSimMessage.remove_actors.CopyFrom(remove_actors)
        return toSimMessage

    def add_counter(self, counter):
        if counter.actor_name in self.ms_removed:
            return
        if counter.actor_name not in self.weight_per_ms:
            self.weight_per_ms[counter.actor_name] = 0.5
        if counter.metric == 'cpu_usage':
            self.number_of_ms += 1
            self.total_cpu_usage += counter.value
        elif counter.metric == 'overflow':
            self.total_overflow += counter.value

    def updateParams(self):
        while True:
            time.sleep(0.5)

    def run(self):
        x = threading.Thread(target=self.updateParams)
        x.start()