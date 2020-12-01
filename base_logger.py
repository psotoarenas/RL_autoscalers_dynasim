
import logging
default_extra = {}

#extra = {'name': 'RA', 'sim_time': '2000/1/1 0:00:28 {56,8}', 'node': 'localhost'}

logging.basicConfig(format='<0.0.0>|%(app_name)s|Python|%(sim_time)s|%(asctime)s|%(node)s|uncategorized|4|%(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S', filename='python.traces', level=logging.DEBUG)
logger = logging


def m_log(message, timemanager):
    sim_time = "{} {}".format(timemanager.getCurrentSimulationTimeString(), timemanager.getCurrentTickOffsetString())
    logger.info(message, extra={**{'sim_time': sim_time}, **default_extra})

