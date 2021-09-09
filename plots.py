import os
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3.common import results_plotter
from stable_baselines3.common.results_plotter import load_results, ts2xy
import pandas as pd
from matplotlib.gridspec import GridSpec

def moving_average(values, window):
    """
    Smooth values by doing a moving average
    :param values: (numpy array)
    :param window: (int)
    :return: (numpy array)
    """
    weights = np.repeat(1.0, window) / window
    return np.convolve(values, weights, 'valid')


def plot_results(log_folder, num_timesteps, title='Learning Curve'):
    """
    plot the results

    :param log_folder: (str) the save location of the results to plot
    :param title: (str) the title of the task to plot
    """
    data_frame = load_results(log_folder)
    if num_timesteps is not None:
        data_frame = data_frame[data_frame.l.cumsum() <= num_timesteps]
    x, y = ts2xy(data_frame, 'timesteps')

    fig = plt.figure(title)
    plt.plot(x, y)
    plt.xlabel('Number of Timesteps')
    plt.ylabel('Rewards')
    plt.title(title + " Smoothed")
    plt.savefig('./train_rewards.png', dpi=300)
    plt.show()
    return


def plot_episodes(log_folder, title='Episode Length Curve'):
    dataframe = load_results(log_folder)
    x = np.cumsum(dataframe.l.values)
    y = dataframe.l.values

    fig = plt.figure(title)
    plt.plot(x, y)
    plt.xlabel('Number of Timesteps')
    plt.ylabel('Episode Lengths')
    plt.title(title + " Smoothed")
    plt.savefig('./train_episode_length.png', dpi=300)
    plt.show()
    return

# traces_filename = "../python.traces"
experiment = "exp-dqn-dynasim-300000-500000-2-1"
root_folder = "/home/darpa/dynamicsim/dynamicsim_ai/"
os.chdir(os.path.join(root_folder, experiment))
traces_filename = experiment + ".traces"

# initialize dicts
modes = ["training", "testing"]
jobs = {key: [] for key in modes}
ms = {key: [] for key in modes}
cpu_usage = {key: [] for key in modes}
overflow = {key: [] for key in modes}
peak_latency = {key: [] for key in modes}
avg_latency = {key: [] for key in modes}
action = {key: [] for key in modes}
reward = {key: [] for key in modes}
cum_reward = {key: [] for key in modes}
reward_cum = {key: [] for key in modes}
current_timesteps = {key: [] for key in modes}
restarts_per_episode = {key: {} for key in modes}
timesteps = {}

act_2_meaning = {
    0: "increase",
    1: "decrease",
    2: "nothing"
}

# Parse results
with open(traces_filename) as f:
    mode = modes[0]
    current_step = 0
    cumulative_reward = 0
    for line in f:
        line = line.rstrip().split("|")[-1]
        if line.startswith("Mode"):
            mode = line.split(":")[-1].rstrip().split()[0]
            timesteps[mode] = int(line.split(":")[-1].rstrip().split()[2])
            if mode == "training": timesteps["base"] = int(line.split(":")[-1].rstrip().split()[-2])
        if line.startswith("Step"):
            current_step = int(line.split(":")[-1].rstrip())
            current_timesteps[mode].append(current_step)
        if line.startswith("Environment Reset"):
            if not restarts_per_episode[mode]:
                # dict is empty
                restarts_per_episode[mode] = []
            if current_step != 0:
                # if it is not the first step
                restarts_per_episode[mode].append(current_step)
                cum_reward[mode].append(cumulative_reward)
        if line.startswith("Traffic"):
            jobs[mode].append(int(line.split(":")[-1].rstrip()))
        if line.startswith("MS"):
            ms[mode].append(int(line.split(":")[-1].rstrip()))
        if line.startswith("Cpu"):
            cpu_usage[mode].append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Overflow"):
            overflow[mode].append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Peak Latency"):
            peak_latency[mode].append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Avg Latency"):
            avg_latency[mode].append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Reward"):
            reward[mode].append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Cum Reward"):
            cumulative_reward = float(line.split(":")[-1].rstrip())
            reward_cum[mode].append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Action"):
            line = line.split(",")[0]
            action[mode].append(act_2_meaning[int(line.split(":")[-1].rstrip())])
        if line.startswith("Agent end training"):
            print(line)
    # first episode testing is actually the last training episode.
    # get values and delete from incorrect list
    last_cum_reward_train = cum_reward["testing"].pop(0)
    last_episode_len_train = restarts_per_episode["testing"].pop(0)
    # add to the correct list
    cum_reward["training"].append(last_cum_reward_train)
    restarts_per_episode["training"].append(last_episode_len_train)
    # add last episode testing
    cum_reward["testing"].append(cumulative_reward)
    restarts_per_episode["testing"].append(current_step)


# --------------- workload ------------------------------
plt.figure()
plt.plot(np.array(jobs["training"])/300., label="workload")
plt.title("workload in training")
plt.savefig('./workload_train.png', dpi=300)
plt.show()

# --------------- can be discarded ------------------------------
plt.figure()
plt.plot(np.array(ms["training"]), label="ms")
plt.title("number of ms in training")
plt.savefig('./ms_train.png', dpi=300)
# plt.show()

# --------------- can be discarded ------------------------------
plt.figure()
plt.plot(np.array(cpu_usage["training"]))
plt.title("cpu usage in training")
plt.savefig('./cpu_train.png', dpi=300)
# plt.show()

# --------------- can be discarded ------------------------------
plt.figure()
plt.plot(np.array(overflow["training"]))
plt.title("overflow in training")
plt.savefig('./overflow_train.png', dpi=300)
# plt.show()

# --------------- can be discarded ------------------------------
plt.figure()
plt.plot(np.array(peak_latency["training"]))
plt.title("peak latency[sec] in training")
plt.savefig('./peak_latency_train.png', dpi=300)
plt.show()

plt.figure()
plt.plot(np.array(avg_latency["training"]))
plt.title("avg latency[sec] in training")
plt.savefig('./avg_latency_train.png', dpi=300)
plt.show()

plt.figure()
plt.plot(action["training"], 'o')
plt.title("actions in training")
plt.savefig('./actions_train.png', dpi=300)
plt.show()

# ---------------------------- immediate rewards  ---------------------------------------------------------
plt.figure()
plt.plot(np.array(reward["training"]))
plt.title("rewards in training")
plt.savefig('./rewards_train.png', dpi=300)
plt.show()
# ------------------------------------------------------------------------------------------------------------

# ---------------------------- cumulative rewards (from SB)  ---------------------------------------------------------
x = np.cumsum(np.array(restarts_per_episode["training"]))
y = np.array(cum_reward["training"])
plt.figure()
plt.plot(x, y)
plt.xlabel('Number of Timesteps')
plt.ylabel('Rewards')
plt.title("cum. reward in training")
plt.savefig('./cum_reward_train.png', dpi=300)
plt.show()
# ------------------------------------------------------------------------------------------------------------
# ---------------------------- episode length (from SB) ---------------------------------------------------------
x = np.cumsum(np.array(restarts_per_episode["training"]))
y = np.array(restarts_per_episode["training"])
plt.figure()
plt.plot(x, y)
plt.xlabel('Number of Timesteps')
plt.ylabel('Rewards')
plt.title("Episode Length Curve in training")
plt.savefig('./len_episode_train.png', dpi=300)
plt.show()
# ------------------------------------------------------------------------------------------------------------

# ---------------------------- cumulative rewards (own) ---------------------------------------------------------
plt.figure()
plt.plot(np.array(reward_cum["training"]))
plt.xlabel('Number of Timesteps')
plt.ylabel('Rewards')
plt.title("cum. reward in training")
plt.savefig('./reward_cum_train.png', dpi=300)
plt.show()
# ------------------------------------------------------------------------------------------------------------
# ---------------------------- episode length (own)  ---------------------------------------------------------
plt.figure()
plt.plot(np.array(current_timesteps["training"]))
plt.xlabel('Number of Timesteps')
plt.ylabel('Episode Length')
plt.title("Episode Length Curve in training")
plt.savefig('./episode_len_train.png', dpi=300)
plt.show()
# ------------------------------------------------------------------------------------------------------------

# ##################### Plot testing figures #############################################################
plt.figure()
# every ms can process 300 jobs per tick, jobs/300 will give the right amount of MS the system will need
plt.plot(np.array(jobs["testing"])/300.)
plt.title("workload in testing")
plt.savefig('./workload_test.png', dpi=300)
plt.show()

plt.figure()
plt.plot(np.array(ms["testing"]))
plt.title("number of ms in testing")
plt.savefig('./ms_test.png', dpi=300)
plt.show()

plt.figure()
plt.plot(np.array(cpu_usage["testing"]), label="cpu")
plt.plot(np.array(overflow["testing"]), label="overflow")
plt.ylim([0, 4])
plt.title("cpu | overflow in testing")
plt.legend()
plt.savefig('./cpu_overflow_test.png', dpi=300)
plt.show()

plt.figure()
plt.plot(np.array(peak_latency["testing"]))
plt.ylim([0, 0.1])
plt.title("peak latency[sec] in testing")
plt.savefig('./peak_latency_test.png', dpi=300)
plt.show()

plt.figure()
plt.plot(np.array(avg_latency["testing"]))
plt.ylim([0, 0.1])
plt.title("avg latency[sec] in testing")
plt.savefig('./avg_latency_test.png', dpi=300)
plt.show()

plt.figure()
plt.plot(action["testing"], 'o')
plt.title("actions in testing")
plt.savefig('./actions_test.png', dpi=300)
plt.show()

plt.figure()
plt.plot(np.array(reward["testing"]))
plt.title("rewards in testing")
plt.savefig('./rewards_test.png', dpi=300)
plt.show()

# plots for paper
fontsize=12

fig = plt.figure(constrained_layout=True, figsize=(12,3))
gs = GridSpec(2, 3, figure=fig)
ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(np.array(ms["testing"]), label='VNF')
ax1.set_title('Num VNFs', fontsize=fontsize)
ax2 = fig.add_subplot(gs[1, 0])
ax2.plot(np.array(jobs["testing"])/300., label='Work')
ax2.set_xlabel('Timesteps', fontsize=fontsize)
ax2.set_title('Workload', fontsize=fontsize)
ax2.sharex(ax1)
ax3 = fig.add_subplot(gs[0:, 1])
ax3.plot(np.array(peak_latency["testing"]), label='peak_lat')
ax3.set_xlabel('Timesteps', fontsize=fontsize)
ax3.set_title('Peak Latency [sec]', fontsize=fontsize)
ax4 = fig.add_subplot(gs[0:, 2])
ax4.plot(np.array(cpu_usage["testing"]), label='cpu')
ax4.plot(np.array(overflow["testing"]), label='overflow')
ax4.set_xlabel('Timesteps', fontsize=fontsize)
ax4.set_title('CPU Usage [%] |Overflow [Num_jobs]', fontsize=fontsize)
ax4.legend()

plt.savefig('./results_paper.png', dpi=300)
plt.show()


# Statistics
df = pd.DataFrame({'num_ms': ms["testing"], 'peak_latency': peak_latency["testing"]})
print(df.describe())

# Plots from stable-baselines3
# Helper from the library
results_plotter.plot_results([os.path.join(root_folder, experiment)], timesteps["training"], results_plotter.X_TIMESTEPS, "Dynasim")
plt.show()
# function based implemented with helpers from SB
plot_results(os.path.join(root_folder, experiment), timesteps["training"])
# function based implemented with helpers from SB
plot_episodes(os.path.join(root_folder, experiment))