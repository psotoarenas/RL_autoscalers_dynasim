from Environment import DynaSimEnv
import time
import argparse
import docker
import sys
import base_logger
import os

########################################################################################################################
# Define constants.
########################################################################################################################
# define target latency = 20ms
target_latency = 0.02
# define target CPU = 75% usage
target_cpu = 0.75
# define a tolerance of 20% the target
tolerance = 0.2

########################################################################################################################
# Command line arguments.
########################################################################################################################

parser = argparse.ArgumentParser(description='RL training using sim-diasca')
parser.add_argument('--timesteps_eval', default=10000, type=int, help='Number of interactions for evaluating agent')
parser.add_argument('--sim_length', default=20000, type=int, help='Number of ticks per second to be simulated')
parser.add_argument('--ticks_per_second', default=1, type=int, help='Ticks per second')
parser.add_argument('--report_ticks', default=5, type=int, help='How many ticks a report is generated')
parser.add_argument('--agent_name', default='rule-dynasim', help='Agent Name')
parser.add_argument('--ip', default='127.0.0.1', help='IP where the python (AI) script is running')

args = parser.parse_args()

########################################################################################################################
# Train Agent during timesteps_train and simulation length in ticks terms
########################################################################################################################

# every incoming report is considered an interaction with the simulator. Therefore, the simulation length (in ticks)
# should be set by the number of timesteps (interactions with the simulator) and the number of report ticks.
# simulation length should be longer than the number of timesteps (train or evaluation) to gracefully finish the process
timesteps = args.timesteps_eval

sim_length = args.sim_length
if not (sim_length >= (timesteps + 2) * args.report_ticks):
    sys.exit("Simulation ticks must be larger than the timesteps for training or testing. "
             "At least sim_length = (timesteps + 2) * report_ticks")
# logger
base_logger.default_extra = {'app_name': f'{args.agent_name}', 'node': 'localhost'}

########################################################################################################################
# Create dir for saving results
########################################################################################################################

results_dir = f"exp-{args.agent_name}-{timesteps}-{args.report_ticks}"
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

########################################################################################################################
# Deploy Agent.
########################################################################################################################

base_logger.info(f"Mode: testing for {timesteps} timesteps")
start = time.time()

# this is a rule-based agent, it will increase the number of ms if the peak latency is above a threshold,
# decrease the number of ms if the peak latency is below a threshold and
# do nothing if the peak latency is within a threshold. Action is an integer with the following meaning:
# {0: "increase", 1: "decrease", 2: "nothing"}
latency = 0.0033
cpu = 0.5
state = env.reset()
for timestep in range(timesteps):
    if (latency - target_latency > target_latency * tolerance) or (cpu - target_cpu > target_cpu * tolerance):
        # increase the num of ms, cause the latency or the cpu usage is high
        action = 0
    elif (latency - target_latency < target_latency * tolerance) or (cpu - target_cpu < target_cpu * tolerance):
        # decrease the num of ms, cause the latency or the cpu usage is low
        action = 1
    else:
        action = 2
    state, reward, done, info = env.step(action)
    cpu, latency, overflow, num_ms = state

end = time.time()

base_logger.info(f"Agent end testing. Elapsed time: {end - start}")

########################################################################################################################
# Clean before you leave
########################################################################################################################

# kill simulation before you leave
container_id = info["container_id"]
client = docker.from_env()
container = client.containers.get(container_id)
print(f"Killing container: {container_id}")
container.stop()  # default time for stopping: 10 secs
container.remove()

########################################################################################################################
# Save your Results.
########################################################################################################################

# Rename python.traces as exp - agent_type - total timesteps - report ticks - experiment
results_filename = f"exp-{args.agent_name}-{timesteps}-{args.report_ticks}-{last_exp + 1}.traces"
print(f"Saving results as {results_filename}")
os.rename("python.traces", os.path.join(results_dir, results_filename))