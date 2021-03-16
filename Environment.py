import gym
from gym import spaces
from EnvironmentCommunicator import DynaSim
import base_logger

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

    def __init__(self, time_steps):
        print("Creating new Dynasim Env")
        super(DynaSimEnv, self).__init__()
        # Define action and observation space
        # They must be gym.spaces objects

        # start communication with simulator in a thread
        print("Starting communication")
        self.dynasim = DynaSim()
        self.x = threading.Thread(target=self.dynasim.run)
        self.x.start()

        # initialize timesteps
        self.current_step = 0

        # Setting discrete actions:
        self.action_space = spaces.Discrete(self.N_DISCRETE_ACTIONS)

        # Example for using image as input:
        self.observation_space = spaces.Box(
            low=0, high=2, shape=(1,), dtype=np.float32)

        # logger
        base_logger.default_extra = {'app_name': 'Environment', 'node': 'localhost'}

        # start simulation
        self.total_timesteps = time_steps
        self.dynasim.start_simulation(self.total_timesteps)

    def step(self, action):
        # need to wait until next report
        self.dynasim.receive_counters = False

        base_logger.info(f"Step: {self.current_step}")
        # print(f"Step: {self.current_step}")

        meaning = act_2_meaning[action]
        base_logger.info(f"Action: {action}, {meaning}")
        # print(f"Action: {action}, {meaning}")

        # take an action (according to a learned behavior)
        self._take_action(action)

        self.current_step += 1

        # when the next report is ready EnvironmentCommunicator.py will change the receive_counters flag to True
        # block the code execution until the report is received
        while not self.dynasim.receive_counters:
            pass

        # observe the effect of the action on the simulation status
        obs = self._next_observation()

        # assign a reward
        if obs > 1 or obs < 0.5:
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
    # two timesteps are lost the first timestep to make the first observation and the last timestep to leave the simulation hanging
    timesteps_train = 100
    timesteps_simulation = timesteps_train + 2
    # without vectorized environments
    env = DynaSimEnv(timesteps_simulation)
    # Random Actions from action space -> the same as agent.learn but without saving to memory (learning)
    print(f"Action Space: {env.action_space}")
    print(f"Observation Space: {env.observation_space}")
    observation = env.reset()
    for _ in range(timesteps_train):
        env.render()
        print(f"Observation: {observation}")
        action = env.action_space.sample()
        observation, reward, done, info = env.step(action)
    print("End")
