import threading
import time
import x_pb2
import random


class RewardOptimizer:
    def __init__(self):
        self.number_of_ms = 0

    def getUpdate(self):
        self.number_of_ms += 1

    def updateParams(self):
        while True:
            time.sleep(0.5)

    def run(self):
        x = threading.Thread(target=self.updateParams)
        x.start()