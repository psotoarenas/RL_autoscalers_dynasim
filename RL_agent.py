from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3 import DQN
from Environment import DynaSimEnv
import time
import argparse
import os
import docker
import sys
import base_logger
import numpy as np

########################################################################################################################
# Command line arguments.
########################################################################################################################

parser = argparse.ArgumentParser(description='RL training using sim-diasca')
parser.add_argument('--timesteps_train', default=10000, type=int, help='Number of interactions for training agent')
parser.add_argument('--timesteps_eval', default=10000, type=int, help='Number of interactions for evaluating agent')
parser.add_argument('--timesteps_base', default=10000, type=int, help='Minimum number of timesteps in an episode')
parser.add_argument('--sim_length', default=20000, type=int, help='Number of ticks per second to be simulated')
parser.add_argument('--ticks_per_second', default=1, type=int, help='Ticks per second')
parser.add_argument('--report_ticks', default=5, type=int, help='How many ticks a report is generated')
parser.add_argument('--agent_name', default='dqn-dynasim', help='Agent Name')
parser.add_argument('--ip', default='127.0.0.1', help='IP where the python (AI) script is running')

args = parser.parse_args()

########################################################################################################################
# Train Agent during timesteps_train and simulation length in ticks terms
########################################################################################################################

# every incoming report is considered an interaction with the simulator. Therefore, the simulation length (in ticks)
# should be set by the number of timesteps (interactions with the simulator) and the number of report ticks.
# simulation length should be longer than the number of timesteps (train or evaluation) to gracefully finish the process
timesteps_train = args.timesteps_train
timesteps_eval = args.timesteps_eval

# check which of the two timesteps is longer
if timesteps_train > timesteps_eval:
    time_steps = timesteps_train
else:
    time_steps = timesteps_eval

sim_length = args.sim_length
if not (sim_length >= (time_steps + 2) * args.report_ticks):
    sys.exit("Simulation ticks must be larger than the timesteps for training or testing. "
             "At least sim_length = (timesteps + 2) * report_ticks")
# logger
base_logger.default_extra = {'app_name': 'DQN_Agent', 'node': 'localhost'}

########################################################################################################################
# Vectorize Environment.
########################################################################################################################

env = DynaSimEnv(sim_length=sim_length, ai_ip=args.ip, ticks=args.ticks_per_second, report=args.report_ticks)
# wrap it
env = make_vec_env(lambda: env, n_envs=1)

########################################################################################################################
# Create Agent.
########################################################################################################################

# to replace the agent, simply invoke another method
agent = DQN('MlpPolicy', env, verbose=1)

########################################################################################################################
# Train Agent.
########################################################################################################################

timesteps_base = args.timesteps_base
base_logger.info(f"Mode: training for {timesteps_train} timesteps with {timesteps_base} base")
start = time.time()

# the training is now per episodes. episodes = timesteps_train / timesteps_base
# if the simulation is not restarted, the agent is able to see a pattern of timesteps_base the number of episodes
episodes = int(float(timesteps_train)/float(timesteps_base))

if episodes < 1:
    sys.exit("The number of timesteps for training should be bigger than the timesteps_base")

for episode in range(episodes):
    base_logger.info(f"Episode: {episode}")
    # inside the learn loop: reset the environment, make an observation, take an  action, obtain reward,
    # save to memory buffer and repeat for the number of timesteps.
    agent.learn(total_timesteps=timesteps_base)

end = time.time()

base_logger.info(f"Agent end training. Elapsed time: {end - start}")

########################################################################################################################
# Save Agent.
########################################################################################################################

agent_name = "{}-{}-{}-{}-{}".format(args.agent_name, timesteps_train, timesteps_base, timesteps_eval, args.report_ticks)
print(f"Saving agent as {agent_name}")
agent.save(agent_name)
print("Training procedure finished")

########################################################################################################################
# Evaluate your Agent for timesteps_eval.
########################################################################################################################

timesteps_eval = args.timesteps_eval
timestep_rewards = [0.0]
episode_rewards = [0.0]
cpu_usage = []
overflow = []
latency = []
num_ms = []
actions = []
rewards = []
print(f"Agent {agent_name} will be evaluated")
base_logger.info(f"Mode: testing for {timesteps_eval} timesteps")

obs = env.reset()
for i in range(timesteps_eval):
    # _states are only useful when using LSTM policies
    action, _states = agent.predict(obs)

    obs, reward, done, info = env.step(action)

    cpu_usage.append(obs[0, 0])
    latency.append(obs[0, 1])
    overflow.append(obs[0, 2])
    num_ms.append(obs[0, 3])
    rewards.append(reward[0])
    actions.append(info[0]["action"])

    # Stats
    episode_rewards[-1] += reward[0]
    if done:
        obs = env.reset()
        episode_rewards.append(0.0)

base_logger.info("Agent evaluation finished")

# Compute mean reward for the last 100 episodes
mean_100ep_reward = round(np.mean(episode_rewards[-100:]), 1)
print("Mean reward:", mean_100ep_reward, "Num episodes:", len(episode_rewards))

# kill simulation before you leave
container_id = info[0]["container_id"]
client = docker.from_env()
container = client.containers.get(container_id)
print(f"Killing container: {container_id}")
container.stop()  # default time for stopping: 10 secs
# time.sleep(20)


########################################################################################################################
# Save your Results.
########################################################################################################################

# Rename python.traces as exp - training steps (in K) - base steps - testing steps (in K) - report ticks - reward function
# Remember to change the reward function.
results_filename = "exp-{}-{}-{}-{}-4.traces".format(timesteps_train, timesteps_base, timesteps_eval, args.report_ticks)
print(f"Saving results as {results_filename}")
os.rename("python.traces", results_filename)
