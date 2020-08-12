import time

class TimeManagement:

    def __init__(self):
        self.start_time = 0
        self.tick_interval = 0

    def initializeTime(self, tick_interval):
        self.start_time = time.time()

    def updateTime(self):
        self.start_time