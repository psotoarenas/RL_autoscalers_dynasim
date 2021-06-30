from stable_baselines.deepq.policies import MlpPolicy
from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines import DQN
from Environment import DynaSimEnv
import time
import argparse
import matplotlib.pyplot as plt
import os
import signal
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
parser.add_argument('--sim_length', default=20000, type=int, help='Number of ticks per second to be simulated')
parser.add_argument('--ticks_per_second', default=1, type=int, help='Ticks per second')
parser.add_argument('--report_ticks', default=5, type=int, help='How many ticks a report is generated')
parser.add_argument('--agent_name', default='dqn_dynasim', help='Agent Name')
parser.add_argument('--ip', default='127.0.0.1', help='IP where the python (AI) script is running')
parser.add_argument('--sim_dir', default='../dynamicsim/mock-simulators/dynaSim/test/',
                    help='Directory where the command to start the simulation needs to run')

args = parser.parse_args()

########################################################################################################################
# Train Agent during timesteps_train and simulation length in ticks terms
########################################################################################################################

# todo: double check if this is still needed
timesteps_train = args.timesteps_train
sim_length = args.sim_length
# simulation length should be longer than the number of timesteps to gracefully finish the process
if not (sim_length >= (timesteps_train + 2) * args.ticks_per_second):
    sys.exit("Simulation ticks must be larger than the timesteps for training. "
             "At least sim_length = (timesteps_train + 2) * ticks_per_second")
# logger
base_logger.default_extra = {'app_name': 'DQN_Agent', 'node': 'localhost'}

########################################################################################################################
# Vectorize Environment.
########################################################################################################################

env = DummyVecEnv([lambda: DynaSimEnv(sim_length=sim_length, ai_ip=args.ip, sim_dir=args.sim_dir,
                                      ticks=args.ticks_per_second, report=args.report_ticks)])

########################################################################################################################
# Create Agent.
########################################################################################################################

# to replace the agent, simply invoke another method
agent = DQN(MlpPolicy, env, verbose=1, tensorboard_log="./dynasim_agent_tensorboard")

########################################################################################################################
# Train Agent.
########################################################################################################################

base_logger.info(f"Mode: training for {timesteps_train} timesteps")
start = time.time()

# the training is now per episodes. episodes = timesteps_train / 10000 (base)
# if the simulation is not restarted, the agent is able to see the pattern of 10k timesteps the number of episodes
episodes = int(float(timesteps_train))

for episode in range(episodes):
    # inside the learn loop: reset the environment, make an observation, take an  action, obtain reward,
    # save to memory buffer and repeat for the number of timesteps.
    agent.learn(total_timesteps=10000)

end = time.time()

base_logger.info(f"Agent end training. Elapsed time: {end - start}")

########################################################################################################################
# Save Agent.
########################################################################################################################

agent_name = args.agent_name
print(f"Saving agent as {agent_name}")
agent.save(agent_name)
print("Training procedure finished")

########################################################################################################################
# Test the trained agent for timesteps_eval
########################################################################################################################

timesteps_evaluation = args.timesteps_eval

########################################################################################################################
# Evaluate your Agent.
########################################################################################################################

timestep_rewards = [0.0]
episode_rewards = [0.0]
obs = env.reset()
observations = []
num_ms = []
print(f"Agent {agent_name} will be evaluated")
base_logger.info(f"Mode: testing for {timesteps_evaluation} timesteps")

for i in range(timesteps_evaluation):
    # _states are only useful when using LSTM policies
    action, _states = agent.predict(obs)

    obs, reward, done, info = env.step(action)

    observations.append(obs[0, 0])
    num_ms.append(info[0]["num_ms"])

    # Stats
    episode_rewards[-1] += reward
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
# Plot your Results.
########################################################################################################################

print("Plotting results")
plt.plot(observations)
plt.ylabel('Observation')
plt.xlabel('Timesteps')
# plt.savefig('./cpu_usage.png', dpi=300)
plt.show()

plt.plot(num_ms)
plt.ylabel('Number of MS')
plt.xlabel('Timesteps')
# plt.savefig('./num_ms.png', dpi=300)
plt.show()

