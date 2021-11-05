from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3 import DQN
from Environment import DynaSimEnv
import time
import numpy as np
import argparse
import os
import sys
import base_logger
import wandb

########################################################################################################################
# Command line arguments.
########################################################################################################################

parser = argparse.ArgumentParser(description='RL training using sim-diasca')
parser.add_argument('--sim_length', default=20000, type=int, help='Number of ticks per second to be simulated')
parser.add_argument('--ticks_per_second', default=1, type=int, help='Ticks per second')
parser.add_argument('--report_ticks', default=5, type=int, help='How many ticks a report is generated')
parser.add_argument('--ip', default='127.0.0.1', help='IP where the python (AI) script is running')
parser.add_argument('--run_id', default='psotoarenas/DynamicSIM-RL/<run_id>', help='WANDB run_id')
parser.add_argument('--push', default=5557, type=int, help='ZMQ push port')
parser.add_argument('--pull', default=5556, type=int, help='ZMQ pull port')

args = parser.parse_args()

agent_name = "DQN"

########################################################################################################################
# Train Agent during timesteps and simulation length in ticks terms
########################################################################################################################

# every incoming report is considered an interaction with the simulator. Therefore, the simulation length (in ticks)
# should be set by the number of timesteps (interactions with the simulator) and the number of report ticks.
# simulation length should be longer than the number of timesteps (train or evaluation) to gracefully finish the process
timesteps = 172800  # fixed to test with an unseen trace (last 172800 seconds of the workload trace)

sim_length = args.sim_length
if not (sim_length >= (timesteps + 2) * args.report_ticks):
    sys.exit("Simulation ticks must be larger than the timesteps for training or testing. "
             "At least sim_length = (timesteps + 2) * report_ticks")
# logger
base_logger.default_extra = {'app_name': f'{agent_name}', 'node': 'localhost'}

########################################################################################################################
# Create dir for saving results
########################################################################################################################


results_dir = f"test-{agent_name}-{timesteps}-{args.report_ticks}"
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

env = DynaSimEnv(sim_length=sim_length,
                 ai_ip=args.ip,
                 ticks=args.ticks_per_second,
                 report=args.report_ticks,
                 mode='test',
                 pull=args.pull,
                 push=args.push,
                 )
# wrap it
env = make_vec_env(lambda: env, n_envs=1, monitor_dir=results_dir)

########################################################################################################################
# Download Agent.
########################################################################################################################

config = {
    "policy_type": "MlpPolicy",
    "total_timesteps": timesteps,
    "env_name": "Dynasim",
    "agent_name": agent_name,
    "mode": "test"
}

run = wandb.init(
    project="DynamicSIM-RL",
    config=config,
    sync_tensorboard=True,  # auto-upload sb3's tensorboard metrics
    monitor_gym=False,  # auto-upload the videos of agents playing the game
    save_code=True,  # optional
    )

wandb.config.update(args)


# Download Trained Agent
api = wandb.Api()

train_run = api.run(args.run_id)
for file in train_run.files():
    if file.name.startswith(agent_name):
        model = file.name
        print(f"Retrieving {model} from {args.run_id}")
        train_run.file(model).download(root=results_dir, replace=True)

########################################################################################################################
# Import Agent.
########################################################################################################################

agent = DQN.load(os.path.join(results_dir, model))
base_logger.info(f"Saving evaluation in {results_dir} for agent in {args.run_id}")

########################################################################################################################
# Evaluate your Agent.
########################################################################################################################

episode_rewards = [0.0]
base_logger.info(f"Mode: testing for {timesteps} timesteps")
start = time.time()

state = env.reset()
for i in range(timesteps):
    # _states are only useful when using LSTM policies
    action, _states = agent.predict(state)

    state, reward, done, info = env.step(action)

    # Stats
    episode_rewards[-1] += reward
    if done:
        # state = env.reset()
        episode_rewards.append(0.0)

end = time.time()
base_logger.info("Agent evaluation finished")

# Compute mean reward for the last 100 episodes
mean_100ep_reward = np.mean(episode_rewards[-100:])
print("Mean reward:", mean_100ep_reward, "Num episodes:", len(episode_rewards))

########################################################################################################################
# Save your Results and clean.
########################################################################################################################

# Rename python.traces as exp - agent_name - testing steps - report ticks - experiment
results_filename = f"{agent_name}-{timesteps}-{args.report_ticks}-{last_exp + 1}.traces"

print(f"Saving results as {results_filename}")
os.rename("python.traces", os.path.join(results_dir, results_filename))

# upload data to wandb server
wandb.config.execution_time = end - start
wandb.save("Environment.py")
logger = base_logger.file_handler.baseFilename.split("/")[-1]
print(f"Logger: {logger}")
wandb.save(logger)
print("Testing procedure finished")

# kill simulation before you leave
run.finish()
env.close()