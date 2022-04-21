from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3 import PPO
from Environment import DynaSimEnv
import time
import argparse
import os
import sys
import base_logger
import wandb
from wandb.integration.sb3 import WandbCallback


########################################################################################################################
# Command line arguments.
########################################################################################################################

parser = argparse.ArgumentParser(description='RL training using sim-diasca')
parser.add_argument('--timesteps', default=10000, type=int, help='Number of interactions for training agent')
parser.add_argument('--sim_length', default=20000, type=int, help='Number of ticks per second to be simulated')
parser.add_argument('--ticks_per_second', default=1, type=int, help='Ticks per second')
parser.add_argument('--report_ticks', default=5, type=int, help='How many ticks a report is generated')
parser.add_argument('--ip', default='127.0.0.1', help='IP where the python (AI) script is running')
parser.add_argument('--push', default=5557, type=int, help='ZMQ push port')
parser.add_argument('--pull', default=5556, type=int, help='ZMQ pull port')
parser.add_argument('--w_adp', default=0.2, type=float, help='adaptation weight')
parser.add_argument('--w_perf', default=0.6, type=float, help='performance weight')
parser.add_argument('--w_res', default=0.2, type=float, help='resource weight')
parser.add_argument('--learning_rate', default=0.0003, type=float, help='learning rate')
parser.add_argument('--gamma', default=0.99, type=float, help='discount factor')
parser.add_argument('--trace_file', default='trafficTrace.csv', type=str, help='trace filename')

args = parser.parse_args()

agent_name = "PPO"

########################################################################################################################
# Train Agent during timesteps and simulation length in ticks terms
########################################################################################################################

# every incoming report is considered an interaction with the simulator. Therefore, the simulation length (in ticks)
# should be set by the number of timesteps (interactions with the simulator) and the number of report ticks.
# simulation length should be longer than the number of timesteps (train or evaluation) to gracefully finish the process
timesteps = args.timesteps

sim_length = args.sim_length
if not (sim_length >= (timesteps + 2) * args.report_ticks):
    sys.exit("Simulation ticks must be larger than the timesteps for training or testing. "
             "At least sim_length = (timesteps + 2) * report_ticks")
# logger
base_logger.default_extra = {'app_name': f'{agent_name}', 'node': 'localhost'}

########################################################################################################################
# Create dir for saving results
########################################################################################################################


results_dir = f"train-{agent_name}-{timesteps}-{args.report_ticks}"
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
# Configure wandb
########################################################################################################################

run = wandb.init(
    project="RL_autoscalers",
    config=args,
    sync_tensorboard=True,  # auto-upload sb3's tensorboard metrics
    monitor_gym=False,  # auto-upload the videos of agents playing the game
    save_code=True,  # optional
    )

wandb.config.update({
    "policy_type": "MlpPolicy",
    "total_timesteps": timesteps,
    "env_name": "Dynasim",
    "agent_name": agent_name,
    "mode": "train",
    "run_id": wandb.run.id
})

config = wandb.config

########################################################################################################################
# Create and wrap the environment.
########################################################################################################################

env = DynaSimEnv(sim_length=sim_length,
                 ai_ip=args.ip,
                 ticks=args.ticks_per_second,
                 report=args.report_ticks,
                 trace_file=args.trace_file,
                 mode='train',
                 pull=args.pull,
                 push=args.push,
                 w_perf=args.w_perf,
                 w_adp=args.w_adp,
                 w_res=args.w_res,
                 )
# wrap it
env = make_vec_env(lambda: env, n_envs=1, monitor_dir=results_dir)

########################################################################################################################
# Create Agent.
########################################################################################################################

# to replace the agent, simply invoke another method
agent = PPO(
    config["policy_type"],
    env, verbose=1,
    tensorboard_log=f"runs/{run.id}",
    learning_rate=config["learning_rate"],
    gamma=config["gamma"]
)

########################################################################################################################
# Train Agent.
########################################################################################################################

base_logger.info(f"Mode: training for {timesteps} timesteps")
start = time.time()

# the training is now per episodes. An episode is the number of steps until the simulation is restarted
# (episode termination). Thus, we might have episodes of different length
# inside the learn loop: reset the environment, make an observation, take an  action, obtain reward,
# save to memory buffer and repeat for the number of timesteps.
callback = WandbCallback(gradient_save_freq=100, model_save_freq=1000, model_save_path=f"models/{run.id}", verbose=2)
agent.learn(total_timesteps=timesteps, callback=callback)

end = time.time()

base_logger.info(f"Agent end training. Elapsed time: {end - start}")

########################################################################################################################
# Save Agent.
########################################################################################################################

agent_name = f"{agent_name}-{timesteps}-{args.report_ticks}-{last_exp + 1}"

print(f"Saving agent as {agent_name}")
agent.save(os.path.join(results_dir, agent_name))
# upload data to wandb server
agent.save(os.path.join(wandb.run.dir, agent_name+".zip"))
wandb.config.execution_time = end - start
wandb.save("Environment.py")
logger = base_logger.file_handler.baseFilename.split("/")[-1]
print(f"Logger: {logger}")
wandb.save(logger)
print("Training procedure finished")

# kill simulation before you leave
run.finish()
env.close()
