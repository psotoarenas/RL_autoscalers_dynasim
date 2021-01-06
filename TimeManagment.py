import time
from datetime import datetime

class TimeManagement:
    def __init__(self):
        self.start_time = 0
        self.current_time = 0
        self.tick_interval = 0
        self.current_tick = 0

    def initializeTime(self, tick_interval):
        self.start_time = time.time()
        self.current_time = time.time()
        self.tick_interval = tick_interval

    def updateTime(self, tick_offset):
        self.current_time = self.start_time + (tick_offset * self.tick_interval)
        self.current_tick = tick_offset

    def getCurrentSimulationTime(self):
        return self.current_time

    def getCurrentSimulationTimeString(self):
        dt_object = datetime.fromtimestamp(self.current_time)
        return dt_object.strftime("%Y/%m/%d %H:%M:%S")

    def getCurrentTickOffsetString(self):
        return "{{{},0}}".format(self.current_tick)
