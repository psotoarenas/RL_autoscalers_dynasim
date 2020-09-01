import time


class TimeManagement:
    def __init__(self):
        self.start_time = 0
        self.current_time = 0
        self.tick_interval = 0

    def initializeTime(self, tick_interval):
        self.start_time = time.time()
        self.current_time = time.time()
        self.tick_interval = tick_interval

    def updateTime(self, tick_offset):
        self.current_time = self.start_time + (tick_offset * self.tick_interval)

    def getCurrentSimulationTime(self):
        return self.current_time

