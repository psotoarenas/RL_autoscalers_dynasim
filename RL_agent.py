from stable_baselines.deepq.policies import MlpPolicy
from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines import DQN
from Environment import DynaSimEnv
import time
import argparse
import matplotlib.pyplot as plt
import os
import signal
import sys

########################################################################################################################
# Command line arguments.
########################################################################################################################

parser = argparse.ArgumentParser(description='RL training using sim-diasca')
parser.add_argument('--timesteps_train', default=10000, type=int, help='Number of interactions for training agent')
parser.add_argument('--timesteps_eval', default=500, type=int, help='Number of interactions for evaluating agent')
parser.add_argument('--sim_length', default=20000, type=int, help='Number of ticks to be simulated')
parser.add_argument('--agent_name', default='dqn_dynasim', help='Agent Name')
parser.add_argument('--ip', default='127.0.0.1', help='IP where the python (AI) script is running')
parser.add_argument('--sim_dir', default='../dynamicsim/mock-simulators/dynaSim/test/', help='Directory where the '
                                                                                             'command to start the '
                                                                                             'simulation needs to run')

args = parser.parse_args()

########################################################################################################################
# Train Agent during timesteps_train and simulation length in ticks terms
########################################################################################################################

timesteps_train = args.timesteps_train
sim_length = args.sim_length
# simulation length should be longer than the number of timesteps to gracefully finish the process
if not (sim_length >= timesteps_train + 2):
    sys.exit("Simulation ticks must be larger than the timesteps for training. "
             "At least sim_length = timesteps_train + 2")

########################################################################################################################
# Vectorize Environment.
########################################################################################################################

env = DummyVecEnv([lambda: DynaSimEnv(sim_length=sim_length, ai_ip=args.ip, sim_dir=args.sim_dir)])

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
agent.learn(total_timesteps=timesteps_train)

end = time.time()

print(f"Agent end training. Elapsed time: {end - start}")

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
obs = env.reset()
observations = []
num_ms = []
print(f"Agent {agent_name} will be evaluated")

for i in range(timesteps_evaluation):
    # _states are only useful when using LSTM policies
    action, _states = agent.predict(obs)

    obs, reward, done, info = env.step(action)

    observations.append(obs[0, 0])
    num_ms.append(info[0]["num_ms"])

print("Agent evaluation finished")

# kill simulation before you leave
pid_sim = info[0]["pid_simulation"]
print(f"Killing process: {pid_sim}")
os.killpg(os.getpgid(pid_sim), signal.SIGKILL)
time.sleep(5)


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

