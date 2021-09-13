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
# Define Callback to save best model.
########################################################################################################################

class SaveOnBestTrainingRewardCallback(BaseCallback):
    """
    Callback for saving a model (the check is done every ``check_freq`` steps)
    based on the training reward (in practice, we recommend using ``EvalCallback``).

    :param check_freq: (int)
    :param log_dir: (str) Path to the folder where the model will be saved.
      It must contains the file created by the ``Monitor`` wrapper.
    :param verbose: (int)
    """
    def __init__(self, check_freq: int, log_dir: str, verbose=1):
        super(SaveOnBestTrainingRewardCallback, self).__init__(verbose)
        self.check_freq = check_freq
        self.log_dir = log_dir
        self.save_path = os.path.join(log_dir, 'best_model')
        self.best_mean_reward = -np.inf

    def _init_callback(self) -> None:
        # Create folder if needed
        if self.log_dir is not None:
            os.makedirs(self.log_dir, exist_ok=True)

    def _on_step(self) -> bool:
        if self.n_calls % self.check_freq == 0:
            # Retrieve training reward
            x, y = ts2xy(load_results(self.log_dir), 'timesteps')
            if len(x) > 0:
                # Mean training reward over the last 100 episodes
                mean_reward = np.mean(y[-100:])
                if self.verbose > 0:
                    print(f"Num timesteps: {self.num_timesteps}")
                    print(f"Best mean reward: {self.best_mean_reward:.2f} - Last mean reward per episode: {mean_reward:.2f}")

                # New best model, you could save the agent here
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    # Example for saving best model
                if self.verbose > 0:
                    print(f"Saving new best model to {self.save_path}.zip")
                self.model.save(self.save_path)
        return True


########################################################################################################################
# Command line arguments.
########################################################################################################################

parser = argparse.ArgumentParser(description='RL training using sim-diasca')
parser.add_argument('--timesteps', default=10000, type=int, help='Number of interactions for training/testing agent')
parser.add_argument('--sim_length', default=20000, type=int, help='Number of ticks per second to be simulated')
parser.add_argument('--ticks_per_second', default=1, type=int, help='Ticks per second')
parser.add_argument('--report_ticks', default=5, type=int, help='How many ticks a report is generated')
parser.add_argument('--agent_name', default='dqn-dynasim', help='Agent Name')
parser.add_argument('--mode', default='train', help='Mode: [train, test]')
parser.add_argument('--agent_location', default='./dqn-dynasim-train', help='Agent Location')
parser.add_argument('--ip', default='127.0.0.1', help='IP where the python (AI) script is running')

args = parser.parse_args()

########################################################################################################################
# Train Agent during timesteps_train and simulation length in ticks terms
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
base_logger.default_extra = {'app_name': f'{args.agent_name}', 'node': 'localhost'}

########################################################################################################################
# Main
########################################################################################################################
mode = args.mode
if mode == "train":
########################################################################################################################
# Mode Training
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

    env = DynaSimEnv(sim_length=sim_length, ai_ip=args.ip, ticks=args.ticks_per_second, report=args.report_ticks,
                     mode=mode)
    # wrap it
    env = make_vec_env(lambda: env, n_envs=1, monitor_dir=results_dir)

########################################################################################################################
# Create Agent.
########################################################################################################################

    # to replace the agent, simply invoke another method
    agent = DQN('MlpPolicy', env, verbose=1)

########################################################################################################################
# Train Agent.
########################################################################################################################

    base_logger.info(f"Mode: training for {timesteps} timesteps")
    start = time.time()

    # the training is now per episodes. An episode is the number of steps until the simulation is restarted
    # (episode termination). Thus, we might have episodes of different length
    # inside the learn loop: reset the environment, make an observation, take an  action, obtain reward,
    # save to memory buffer and repeat for the number of timesteps.
    callback = SaveOnBestTrainingRewardCallback(check_freq=1000, log_dir=results_dir)
    agent.learn(total_timesteps=timesteps, callback=callback)

    end = time.time()

    base_logger.info(f"Agent end training. Elapsed time: {end - start}")

########################################################################################################################
# Save Agent.
########################################################################################################################

    agent_name = f"{args.agent_name}-{timesteps}-{args.report_ticks}-{last_exp + 1}"

    print(f"Saving agent as {agent_name}")
    agent.save(os.path.join(results_dir, agent_name))
    print("Training procedure finished")

########################################################################################################################
# Kill Container.
########################################################################################################################
    action = np.array([2])
    state, reward, done, info = env.step(action)
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

    # Rename python.traces as exp - agent_type - training steps - report ticks - experiment
    results_filename = f"exp-{args.agent_name}-{timesteps}-{args.report_ticks}-{last_exp + 1}.traces"
    print(f"Saving results as {results_filename}")
    os.rename("python.traces", os.path.join(results_dir, results_filename))
else:
########################################################################################################################
# Mode Testing
# Create dir for saving results
########################################################################################################################
    results_dir = f"exp-test-{args.agent_name}-{timesteps}-{args.report_ticks}"
    nb_exp = []
    agent_location = args.agent_location
    agent_name = agent_location.split("/")[-1]
    agent_name = agent_name.split("-")[1:]
    agent_name = "-".join(agent_name)
    os.chdir(agent_location)
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

    env = DynaSimEnv(sim_length=sim_length, ai_ip=args.ip, ticks=args.ticks_per_second, report=args.report_ticks,
                     mode=mode)
    # wrap it
    env = make_vec_env(lambda: env, n_envs=1, monitor_dir=results_dir)

########################################################################################################################
# Import Agent.
########################################################################################################################

    agent = DQN.load(agent_name + ".zip")
    base_logger.info(f"Saving evaluation in {results_dir} for agent in {agent_location}")

########################################################################################################################
# Evaluate your Agent for timesteps_eval.
########################################################################################################################

    episode_rewards = [0.0]
    base_logger.info(f"Mode: testing for {timesteps} timesteps")

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
    results_filename = f"exp-{args.agent_name}-{timesteps}-{args.report_ticks}-{last_exp + 1}.traces"
    print(f"Saving results as {results_filename}")
    os.rename("../python.traces", os.path.join(results_dir, results_filename))
