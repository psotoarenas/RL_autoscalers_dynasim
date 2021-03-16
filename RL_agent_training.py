from stable_baselines.deepq.policies import MlpPolicy
from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines import DQN
from Environment import DynaSimEnv
import time
import argparse

########################################################################################################################
# Command line arguments.
########################################################################################################################

parser = argparse.ArgumentParser(description='RL training using sim-diasca')
parser.add_argument('--timesteps', default=100, type=int, help='Number of Timesteps for training procedure')
parser.add_argument('--agent_name', default="dqn_dynasim", help='Agent Name')


args = parser.parse_args()

########################################################################################################################
# Configure timesteps to gracefully terminate process.
########################################################################################################################

timesteps_train = args.timesteps
timesteps_simulation = timesteps_train + 2  # First tick is first observation and last tick hangs.

########################################################################################################################
# Vectorize Environment.
########################################################################################################################

env = DummyVecEnv([lambda: DynaSimEnv(timesteps_simulation)])

########################################################################################################################
# Create Agent.
########################################################################################################################

agent = DQN(MlpPolicy, env, verbose=1)   # to replace the agent, simply invoke another method

########################################################################################################################
# Train Agent.
########################################################################################################################

print(f"Agent training for {timesteps_train} timesteps")
start = time.time()

# inside the learn loop: reset the environment, make an observation, take an  action, obtain reward,
# save to memory buffer and repeat for the number of timesteps.
agent.learn(total_timesteps=timesteps_train, log_interval=100)

end = time.time()

print(f"Agent end training. Elapsed time: {end - start}")

########################################################################################################################
# Save Agent.
########################################################################################################################

agent_name = args.agent_name
print(f"Saving agent as {agent_name}")
agent.save(agent_name)
print("Training procedure finished")
