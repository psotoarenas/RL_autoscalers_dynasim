import math

import gym
from gym import spaces
from EnvironmentCommunicator import DynaSim
import base_logger
import sys

import numpy as np
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
    N_DISCRETE_ACTIONS = 3  # Increase, Decrease, No change the number of MSs (by one)

    # Define constant, discrete actions
    INCREASE = 0
    DECREASE = 1
    NOTHING = 2

    def __init__(self, sim_length, ai_ip, sim_dir, ticks):
        print("Creating new Dynasim Env")
        super(DynaSimEnv, self).__init__()
        # Define action and observation space
        # They must be gym.spaces objects

        # start communication with simulator in a thread
        print("Starting communication")
        self.dynasim = DynaSim()
        self.x = threading.Thread(target=self.dynasim.run)
        self.x.daemon = True  # allows to kill the communication with the simulator
        self.x.start()

        # initialize timesteps
        self.current_step = 0
        self.acc_reward = 0

        # define target latency = 20ms
        self.target = 0.02
        # define a tolerance of 20% the target latency
        self.tolerance = 0.2
        # parameter from paper to tune (no information regarding these values)
        self.alpha = 2.5
        self.beta = 1

        # parameters to start simulation
        self.ip = ai_ip
        self.sim_dir = sim_dir
        self.sim_length = sim_length
        self.ticks = ticks

        # Setting discrete actions:
        self.action_space = spaces.Discrete(self.N_DISCRETE_ACTIONS)

        # Example for using image as input:
        self.observation_space = spaces.Box(low=0, high=np.inf, shape=(4,), dtype=np.float32)

        # logger
        base_logger.default_extra = {'app_name': 'Environment', 'node': 'localhost'}

    def step(self, action):

        base_logger.info(f"Step: {self.current_step}")
        # print(f"Step: {self.current_step}")

        meaning = act_2_meaning[action]
        base_logger.info(f"Action: {action}")
        # print(f"Action: {action}, {meaning}")

        # take an action (according to a learned behavior)
        self._take_action(action)

        self.current_step += 1

        # when the next report is ready EnvironmentCommunicator.py will set report_ready to True
        # block the code execution until the report is received
        self.dynasim.report_ready.wait()

        # observe the effect of the action on the simulation status
        obs = self._next_observation()

        # assign a reward
        # Reward 1: based on latency
        # reward = -abs(obs[1] - self.target)

        # Reward 2: based on latency
        # if -abs(obs[1] - self.target) > self.tolerance:
        #     reward = -1
        # else:
        #     reward = 0

        # Reward 3: based on latency
        # if -abs(obs[1] - self.target) > self.tolerance:
        #     reward = -1
        # else:
        #     reward = -abs((obs[1] - self.target) / (self.tolerance * self.target))

        # Reward 4: based on latency
        if abs(obs[1] - self.target) > self.tolerance * self.target:
            # there are two cases that are not desirable:
            if obs[3] < 2:
                # the agent keeps decreasing the num of MS -> the overflow increases
                reward = -1 * obs[2]
            else:
                # the agent keeps increasing the num of MS -> the obs keeps at minimum
                reward = -1 * obs[3]
        else:
            reward = -(obs[1] - self.target) ** 2

        # Reward 5: based on latency
        # reward = (1 / (obs[1] - self.target)) - (obs[1] - self.target)

        # Reward 6: based on latency
        # reward = -(obs[1] - self.target) ** 2

        # Reward 7: -(latency/target) - (alpha*num_ms*e(-beta*cpu*overflow)
        # reward = -(obs[1] / self.target) - (self.alpha * obs[3] * math.exp(- self.beta * obs[0] * obs[2]))

        self.acc_reward += reward
        base_logger.info(f"Reward: {reward}")
        base_logger.info(f"Target: {self.target}")
        base_logger.info(f"Cum Reward: {self.acc_reward}")

        # if the agent creates more than 100 MSs or the overflow is greater than 500.,
        # end episode and reset simulation
        done = False
        if obs[3] > 100 or obs[2] > 500.:
            done = True
            reward = 10 * reward

        return obs, reward, done, {'num_ms': self.dynasim.number_of_ms,
                                   'action': action,
                                   'pid_simulation': self.dynasim.process.pid}

    def _next_observation(self):
        # observe the simulation status = (cpu, latency, overflow, num_ms)
        cpu, latency, overflow, num_ms = self.dynasim.communicate_counters()
        obs = (cpu, latency, overflow, num_ms)
        return obs

    def _take_action(self, action):
        if action == self.INCREASE:
            self.dynasim.increase_vnf()
        elif action == self.DECREASE:
            self.dynasim.decrease_vnf()

        # get the updated list of messages
        messages = self.dynasim.getUpdate()
        self.dynasim.send_messages(messages)

    def reset(self):
        # stop any previous simulation
        self.dynasim.stop_simulation()

        # start the simulation
        self.dynasim.start_simulation(sim_length=self.sim_length, ip=self.ip, cwd=self.sim_dir, tick_freq=self.ticks)

        # need to wait first_observation=True, that means the simulator is connected and waiting for messages.
        while not self.dynasim.first_observation:
            pass

        print("Environment Reset")
        self.current_step = 0
        return self._next_observation()

    def render(self, mode='human', close=False):
        print(f'Step: {self.current_step}')
        print(f'Num_of_ms: {self.dynasim.number_of_ms}')

if __name__ == "__main__":
    # at least two ticks more are needed in the total simulation length: the first tick to make the first observation
    # and the last tick to be able to finish the process properly
    total_timesteps = 200
    sim_length = 2000
    if not (sim_length >= total_timesteps + 2):
        sys.exit("Simulation ticks must be larger than the timesteps for training. "
                 "At least sim_length = timesteps_train + 2")
    # parameters to start simulation
    ip = input("Specify the IP where the python scripts are running")
    sim_dir = input("Specify the directory where the simulator runs")
    # without vectorized environments
    env = DynaSimEnv(sim_length=sim_length, ai_ip=ip, sim_dir=sim_dir)
    # Random Actions from action space -> the same as agent.learn but without saving to memory (learning)
    print(f"Action Space: {env.action_space}")
    print(f"Observation Space: {env.observation_space}")
    observation = env.reset()
    for i in range(total_timesteps):
        # take random action
        action = env.action_space.sample()
        observation, reward, done, info = env.step(action)
    # the process needs to be killed so it does not remain active after ending the script
    env.dynasim.stop_simulation()
    print("End")
    sys.exit()
