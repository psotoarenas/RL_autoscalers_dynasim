import logging
default_extra = {}
timemanager = None

logger = logging.getLogger('basic-logger')
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('python.traces')
formatter = logging.Formatter('<0.0.0>|%(app_name)s|Python|%(sim_time)s|%(asctime)s|%(node)s|uncategorized|4|%(message)s', datefmt='%d/%m/%Y %H:%M:%S')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def info(message):
    sim_time = "{} {}".format(timemanager.getCurrentSimulationTimeString(), timemanager.getCurrentTickOffsetString())
    logger.info(message, extra={**{'sim_time': sim_time}, **default_extra})

def debug(message):
    sim_time = "{} {}".format(timemanager.getCurrentSimulationTimeString(), timemanager.getCurrentTickOffsetString())
    logger.debug(message, extra={**{'sim_time': sim_time}, **default_extra})

def warning(message):
    sim_time = "{} {}".format(timemanager.getCurrentSimulationTimeString(), timemanager.getCurrentTickOffsetString())
    logger.warning(message, extra={**{'sim_time': sim_time}, **default_extra})

def error(message):
    sim_time = "{} {}".format(timemanager.getCurrentSimulationTimeString(), timemanager.getCurrentTickOffsetString())
    logger.error(message, extra={**{'sim_time': sim_time}, **default_extra})

def critical(message):
    sim_time = "{} {}".format(timemanager.getCurrentSimulationTimeString(), timemanager.getCurrentTickOffsetString())
    logger.critical(message, extra={**{'sim_time': sim_time}, **default_extra})