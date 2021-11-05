import logging
import time
default_extra = {}
timemanager = None

# Create a custom logger
logger = logging.getLogger('basic-logger')
logger.setLevel(logging.DEBUG)

# Create a file handler
timestr = time.strftime("%Y%m%d-%H%M%S")
file_handler = logging.FileHandler(f'python-{timestr}.traces', mode='w')
formatter = logging.Formatter('<0.0.0>|%(app_name)s|Python|%(sim_time)s|%(asctime)s|%(node)s|uncategorized|4|%(message)s', datefmt='%d/%m/%Y %H:%M:%S')
file_handler.setFormatter(formatter)

# Create a console handler
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

# Add handlers to the logger
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