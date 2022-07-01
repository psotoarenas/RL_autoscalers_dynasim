import gym
from gym import spaces
from EnvironmentCommunicator import DynaSim
import base_logger

import numpy as np
import pandas as pd
import threading

act_2_meaning = {
    0: "increase",
    1: "decrease",
    2: "nothing"
}


class DynaSimEnv(gym.Env):
    """A Dynasim environment for OpenAI gym"""
    metadata = {'render.modes': ['human']}

    # Setting discrete actions:
    N_DISCRETE_ACTIONS = 3  # Increase (by one), Decrease (by one), No change the number of MSs

    # Define constant, discrete actions
    INCREASE = 0
    DECREASE = 1
    NOTHING = 2

    def __init__(self, sim_length, ai_ip, ticks, report, trace_file="trafficTrace.csv", mode="train", push=5557, pull=5556, w_adp=0.2, w_perf=0.6, w_res=0.2):
        print("Creating new Dynasim Env")
        super(DynaSimEnv, self).__init__()
        # Define action and observation space
        # They must be gym.spaces objects

        # start communication with simulator in a thread
        print("Starting communication")
        self.dynasim = DynaSim(mode=mode, push=push, pull=pull, trace_file=trace_file)
        self.zmq_com = threading.Thread(target=self.dynasim.run)
        self.zmq_com.daemon = True  # allows to kill the communication with the simulator
        self.zmq_com.start()

        # initialize timesteps
        self.current_step = 0
        self.total_steps = 0
        self.acc_reward = 0
        self.num_restarts = 0

        # define target latency = 20ms
        self.target_latency = 0.02
        # define target cpu = 75% usage
        self.target_cpu = 0.75
        # define a tolerance of 20% the target
        self.tolerance = 0.2
        self.lat_threshold = (1 + self.tolerance) * self.target_latency
        self.cpu_threshold = (1 + self.tolerance) * self.target_cpu
        self.violations = []
        self.vnf = []
        # define weights for the reward function
        self.w_adp = w_adp
        self.w_perf = w_perf
        self.w_res = w_res

        # parameters to start simulation
        self.ip = ai_ip
        self.sim_length = sim_length
        self.ticks = ticks
        self.report = report

        # Setting discrete actions:
        self.action_space = spaces.Discrete(self.N_DISCRETE_ACTIONS)

        # The observation space is a 3-position vector with the metrics: latency, num_ms, cpu
        self.observation_space = spaces.Box(low=0, high=np.inf, shape=(3,), dtype=np.float32)
        self.state = None
        self.prev_state = None

        # logger
        base_logger.default_extra = {'app_name': 'Environment', 'node': 'localhost'}

    def step(self, action):

        base_logger.info(f"Step: {self.current_step}")

        meaning = act_2_meaning[action]
        base_logger.info(f"Action: {action}, {meaning}")

        # take an action (according to a learned behavior)
        self._take_action(action)

        self.current_step += 1
        self.total_steps += 1

        # when the next report is ready EnvironmentCommunicator.py will set report_ready to True
        # block the code execution until the report is received
        self.dynasim.report_ready.wait()

        # observe the effect of the action on the simulation status, get the next state
        self.state = self._next_observation()
        latency, num_ms, cpu = self.state

        prev_latency, prev_ms, prev_cpu = self.prev_state

        # cost function
        ### adaptation cost
        if num_ms == prev_ms:
            adp_cost = 0.
        else:
            adp_cost = 1.

        ### performance cost
        if latency > self.lat_threshold:
            perf_cost = 1.
        else:
            perf_cost = 0.

        ### resource cost
        res_cost = num_ms - prev_ms

        total_cost = (self.w_adp * adp_cost) + (self.w_perf * perf_cost) + (self.w_res * res_cost)

        # # reward 3: compound function
        reward = - total_cost

        # # reward function 1
        # if abs(latency - self.target_latency) < self.target_latency * self.tolerance or \
        #         abs(cpu - self.target_cpu) < self.target_cpu * self.tolerance:
        #     reward = 1
        # else:
        #     reward = 0   # other non-considered cases, for example if the latency is above the thd

        # # reward function 2+: rewarding good actions
        # if prev_latency > self.lat_threshold and action == self.INCREASE and latency <= self.lat_threshold:
        #     reward = 1
        # elif prev_latency <= self.lat_threshold and action == self.DECREASE and latency <= self.lat_threshold:
        #     reward = 1
        # else:
        #     reward = 0  # other non-considered cases
        
        # reward function 2-: penalizing bad actions
        # if prev_latency > self.lat_threshold and action == self.DECREASE and latency >= self.lat_threshold:
        #     reward = -1
        # elif prev_latency <= self.lat_threshold and action == self.DECREASE and latency >= self.lat_threshold:
        #     reward = -1
        # else:
        #     reward = 0  # other non-considered cases

        
        # if the agent creates more than 20 MSs (one server is limited to 53 MS) or the
        # peak latency is above 2 seconds, penalize harder
        done = False
        # todo: include a reset when the number of MS is lower than one (eliminates all the MS)
        if num_ms > 20 or latency > 2.:
            # hard penalization
            reward = -100
            done = True
            # the simulation is going to be restarted, print the accumulated steps
            base_logger.info(f"Total steps: {self.total_steps}")
            # update the numer of restarts
            self.num_restarts += 1

        # done = False
        # # restart the simulation if the number of timesteps is reached
        # if self.current_step % 3600 == 0:
        #     done = True
        #     # the simulation is going to be restarted, print the accumulated steps
        #     base_logger.info(f"Total steps: {self.total_steps}")

        self.acc_reward += reward
        base_logger.info(f"Reward: {reward}")
        # base_logger.info(f"Target: {self.target_latency}")
        base_logger.info(f"Cum Reward: {self.acc_reward}")
        self.prev_state = self.state
        info = {'state': self.state,
                'action': action,
                'reward': reward,
                }

        return self.state, reward, done, info

    def _next_observation(self):
        # observe the simulation status = (cpu, latency, overflow, num_ms)
        latency, num_ms, cpu = self.dynasim.communicate_counters()
        self.state = np.array([latency, num_ms, cpu])
        return self.state

    def _take_action(self, action):
        if action == self.INCREASE:
            self.dynasim.increase_vnf()
        elif action == self.DECREASE:
            self.dynasim.decrease_vnf()

        # get the updated list of messages
        messages = self.dynasim.getUpdate()
        self.dynasim.send_messages(messages)

    def reset(self):
        self.acc_reward = 0
        self.violations = []
        self.vnf = []
        existing_container = self.dynasim.restart_simulation()

        if not existing_container:
            # start the simulation
            self.dynasim.start_simulation(sim_length=self.sim_length, ip=self.ip, tick_freq=self.ticks,
                                          report_ticks=self.report)

        # need to wait first_observation=True, that means the simulator is connected and waiting for messages.
        while not self.dynasim.first_observation:
            pass

        base_logger.info("Environment Reset")
        self.current_step = 0
        self.prev_state = self._next_observation()
        return self.prev_state

    def render(self, mode='human', close=False):
        print(f'Step: {self.current_step}')
        print(f'Num_of_ms: {self.dynasim.number_of_ms}')

    def close(self):
        self.dynasim.stop_simulation()
        base_logger.info(f"Number of restarts {self.num_restarts}")
