from stable_baselines3.common.results_plotter import load_results, ts2xy
from stable_baselines3.common.callbacks import BaseCallback
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
parser.add_argument('--timesteps_eval', default=10000, type=int, help='Number of interactions for evaluating agent')
parser.add_argument('--sim_length', default=20000, type=int, help='Number of ticks per second to be simulated')
parser.add_argument('--ticks_per_second', default=1, type=int, help='Ticks per second')
parser.add_argument('--report_ticks', default=5, type=int, help='How many ticks a report is generated')
parser.add_argument('--agent_name', default='dqn-dynasim', help='Agent Name')
parser.add_argument('--agent_location', default='./dqn-dynasim-train', help='Agent Location')
parser.add_argument('--ip', default='127.0.0.1', help='IP where the python (AI) script is running')

args = parser.parse_args()

########################################################################################################################
# Train Agent during timesteps_train and simulation length in ticks terms
########################################################################################################################

# every incoming report is considered an interaction with the simulator. Therefore, the simulation length (in ticks)
# should be set by the number of timesteps (interactions with the simulator) and the number of report ticks.
# simulation length should be longer than the number of timesteps (train or evaluation) to gracefully finish the process
timesteps_eval = args.timesteps_eval

sim_length = args.sim_length
if not (sim_length >= (timesteps_eval + 2) * args.report_ticks):
    sys.exit("Simulation ticks must be larger than the timesteps for training or testing. "
             "At least sim_length = (timesteps + 2) * report_ticks")
# logger
agent_name = args.agent_name
base_logger.default_extra = {'app_name': f'{agent_name}', 'node': 'localhost'}

########################################################################################################################
# Create dir for saving results
########################################################################################################################

results_dir = f"exp-test-{args.agent_name}-{timesteps_eval}-{args.report_ticks}"
nb_exp = []
for folder_name in os.listdir('./'):
    if folder_name.startswith(results_dir):
        nb_exp.append(int(folder_name.split("-")[-1]))
if nb_exp:
    nb_exp.sort()
    last_exp = nb_exp[-1]
else:
    # first experiment
    last_exp = -1

results_dir = results_dir + "-" + str(last_exp + 1)
os.makedirs(results_dir, exist_ok=True)

########################################################################################################################
# Create and wrap the environment.
########################################################################################################################

env = DynaSimEnv(sim_length=sim_length, ai_ip=args.ip, ticks=args.ticks_per_second, report=args.report_ticks)
# wrap it
env = make_vec_env(lambda: env, n_envs=1, monitor_dir=results_dir)

########################################################################################################################
# Import Agent.
########################################################################################################################

agent_location = args.agent_location
agent = DQN.load(agent_location)
base_logger.info(f"Saving evaluation in {results_dir} for agent in {agent_location}")

########################################################################################################################
# Evaluate your Agent for timesteps_eval.
########################################################################################################################

episode_rewards = [0.0]
print(f"Agent {agent_name} will be evaluated")
base_logger.info(f"Mode: testing for {timesteps_eval} timesteps")

state = env.reset()
for i in range(timesteps_eval):
    # _states are only useful when using LSTM policies
    action, _states = agent.predict(state)

    state, reward, done, info = env.step(action)

    # Stats
    episode_rewards[-1] += reward
    if done:
        state = env.reset()
        episode_rewards.append(0.0)

base_logger.info("Agent evaluation finished")

# Compute mean reward for the last 100 episodes
mean_100ep_reward = np.mean(episode_rewards[-100:])
print("Mean reward:", mean_100ep_reward, "Num episodes:", len(episode_rewards))

# kill simulation before you leave
container_id = info[0]["container_id"]
client = docker.from_env()
container = client.containers.get(container_id)
print(f"Killing container: {container_id}")
container.stop()  # default time for stopping: 10 secs
container.remove()

########################################################################################################################
# Save your Results.
########################################################################################################################

# Rename python.traces as exp - agent_type - testing steps - report ticks - experiment
results_filename = f"exp-{args.agent_name}-{timesteps_eval}-{args.report_ticks}-{last_exp + 1}.traces"
print(f"Saving results as {results_filename}")
os.rename("python.traces", os.path.join(results_dir, results_filename))
