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

    def __init__(self, timesteps, ai_ip, sim_dir):
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

        # total timesteps
        self.timesteps = timesteps

        # parameters to start simulation
        self.ip = ai_ip
        self.sim_dir = sim_dir
        # simulation length should be longer than the number of timesteps to gracefully finish the process
        self.sim_length = self.timesteps * 2

        # Setting discrete actions:
        self.action_space = spaces.Discrete(self.N_DISCRETE_ACTIONS)

        # Example for using image as input:
        self.observation_space = spaces.Box(
            low=0, high=2, shape=(1,), dtype=np.float32)

        # logger
        base_logger.default_extra = {'app_name': 'Environment', 'node': 'localhost'}

    def step(self, action):

        base_logger.info(f"Step: {self.current_step}")
        # print(f"Step: {self.current_step}")

        meaning = act_2_meaning[action]
        base_logger.info(f"Action: {action}, {meaning}")
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
        if obs >= 1.0 or obs < 0.5:
            reward = -1
        else:
            reward = 0

        # we never end, therefore we have a unique episode
        done = False

        return obs, reward, done, {'num_ms': self.dynasim.number_of_ms, 'action': action}

    def _next_observation(self):
        # observe the simulation status
        obs = self.dynasim.communicate_counters()
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
        self.dynasim.start_simulation(total_timesteps=self.sim_length, ip=self.ip, cwd=self.sim_dir)

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
    # parameters to start simulation
    ip = input("Specify the IP where the python scripts are running")
    sim_dir = input("Specify the directory where the simulator runs")
    # without vectorized environments
    env = DynaSimEnv(timesteps=total_timesteps, ai_ip=ip, sim_dir=sim_dir)
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
