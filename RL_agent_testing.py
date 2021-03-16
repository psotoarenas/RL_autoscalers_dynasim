from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines import DQN
from Environment import DynaSimEnv
import matplotlib.pyplot as plt
import argparse


########################################################################################################################
# Command line arguments.
########################################################################################################################

parser = argparse.ArgumentParser(description='RL testing using sim-diasca')
parser.add_argument('--timesteps', default=100, type=int, help='Number of Timesteps for testing procedure')
parser.add_argument('--agent_name', default="dqn_dynasim", help='Agent Name')


args = parser.parse_args()

########################################################################################################################
# Configure timesteps to gracefully terminate process.
########################################################################################################################

timesteps_evaluation = args.timesteps
timesteps_simulation = timesteps_evaluation + 2  # First tick is first observation and last tick hangs.

########################################################################################################################
# Vectorize Environment.
########################################################################################################################

env = DummyVecEnv([lambda: DynaSimEnv(timesteps_simulation)])

########################################################################################################################
# Load your trained Agent.
########################################################################################################################

agent_name = args.agent_name
print(f"Loading agent as {agent_name}")
agent = DQN.load(agent_name)   # the invoked agent has to agree with the trained agent

########################################################################################################################
# Evaluate your Agent.
########################################################################################################################

print(f"Agent {agent_name} is being evaluated")

timestep_rewards = [0.0]
obs = env.reset()
cpu_usage = []
num_ms = []
for i in range(timesteps_evaluation):
    # _states are only useful when using LSTM policies
    action, _states = agent.predict(obs)

    obs, reward, done, info = env.step(action)

    cpu_usage.append(obs[0, 0])
    num_ms.append(info[0]["num_ms"])

print("Agent evaluation finished")

########################################################################################################################
# Plot your Results.
########################################################################################################################

print("Plotting results")
plt.plot(cpu_usage)
plt.ylabel('CPU Usage')
plt.xlabel('Timesteps')
# plt.savefig('./cpu_usage.png', dpi=300)
plt.show()

plt.plot(num_ms)
plt.ylabel('Number of MS')
plt.xlabel('Timesteps')
# plt.savefig('./num_ms.png', dpi=300)
plt.show()