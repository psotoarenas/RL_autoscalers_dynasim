import os
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3.common import results_plotter
from stable_baselines3.common.results_plotter import load_results, ts2xy


def plot_restarts(axis, y_min, y_max, restarts):
    # plot restarts
    y_min = y_min
    y_max = y_max
    line_restarts = None

    for xcoord in restarts:
        line_restarts, = axis.plot([xcoord, xcoord], [y_min, y_max], 'g')
    return line_restarts


def moving_average(values, window):
    """
    Smooth values by doing a moving average
    :param values: (numpy array)
    :param window: (int)
    :return: (numpy array)
    """
    weights = np.repeat(1.0, window) / window
    return np.convolve(values, weights, 'valid')


def plot_results(log_folder, title='Learning Curve'):
    """
    plot the results

    :param log_folder: (str) the save location of the results to plot
    :param title: (str) the title of the task to plot
    """
    x, y = ts2xy(load_results(log_folder), 'timesteps')
    y = moving_average(y, window=50)
    # Truncate x
    x = x[len(x) - len(y):]

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
    y = moving_average(y, window=50)
    # Truncate x
    x = x[len(x) - len(y):]

    fig = plt.figure(title)
    plt.plot(x, y)
    plt.xlabel('Number of Timesteps')
    plt.ylabel('Episode Lengths')
    plt.title(title + " Smoothed")
    plt.savefig('./train_episode_length.png', dpi=300)
    plt.show()
    return


# traces_filename = "/Users/paola/UA/dynamic_sim/python.traces"
experiment = "exp-rule-dynasim-100000-2-0"
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
    episode = 0
    for line in f:
        line = line.rstrip().split("|")[-1]
        if line.startswith("Mode"):
            mode = line.split(":")[-1].rstrip().split()[0]
            timesteps[mode] = int(line.split(":")[-1].rstrip().split()[2])
            if mode == "training": timesteps["base"] = int(line.split(":")[-1].rstrip().split()[-2])
        if line.startswith("Step"):
            current_step = int(line.split(":")[-1].rstrip())
        if line.startswith("Episode"):
            current_step = 0
            episode = int(line.split(":")[-1].lstrip())
        if line.startswith("Environment Reset"):
            if episode not in restarts_per_episode[mode]:
                restarts_per_episode[mode][episode] = []
            restarts_per_episode[mode][episode].append(current_step)
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
        if line.startswith("Action"):
            line = line.split(",")[0]
            action[mode].append(act_2_meaning[int(line.split(":")[-1].rstrip())])
        if line.startswith("Agent end training"):
            print(line)


# Statistics
# # get the restarts. Enable if restarts plot_restarts is used
# xcoords_restart = []
# xcoord = 0
# prev_restart = 0
# for training_episode in restarts_per_episode["training"]:
#     for xcoord in restarts_per_episode["training"][training_episode]:
#         if xcoord == 0:
#             if training_episode != 0:
#                 xcoords_restart.append(training_episode * timesteps["base"])
#                 prev_restart = xcoords_restart[-1]
#             else:
#                 xcoords_restart.append(xcoord)
#         else:
#             xcoords_restart.append(xcoord + prev_restart)
#             prev_restart = xcoords_restart[-1]

# Plot training figures
# every ms can process 300 jobs per tick, jobs/300 will give the right amount of MS the system will need
# # ------------------------- plot with restarts (too noisy) --------------------------------------------------
# _, axis = plt.subplots()
# jobs_handle, = axis.plot(np.array(jobs["training"])/300.)
# y_min = np.min(np.array(jobs["training"])/300.)
# y_max = np.max(np.array(jobs["training"])/300.)
# restart_handle = plot_restarts(axis=axis, y_min=y_min, y_max=y_max, restarts=xcoords_restart)
# plt.legend(handles=[jobs_handle, restart_handle], labels=['workload', 'restarts'], loc='upper right')
# # -----------------------------------------------------------------------------------------------------------
# ---------------------------- plot without restarts  ---------------------------------------------------------
plt.figure()
plt.plot(np.array(jobs["training"])/300., label="workload")
# ------------------------------------------------------------------------------------------------------------
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

# # ------------------------- plot with restarts (too noisy) --------------------------------------------------
# _, axis = plt.subplots()
# rewards_handle, = axis.plot(np.array(reward["training"]))
# y_min = np.min(np.array(reward["training"]))
# y_max = np.max(np.array(reward["training"]))
# restart_handle = plot_restarts(axis=axis, y_min=y_min, y_max=y_max, restarts=xcoords_restart)
# plt.legend(handles=[rewards_handle, restart_handle], labels=['rewards', 'restarts'], loc='upper right')
# # ------------------------------------------------------------------------------------------------------------
# ---------------------------- plot without restarts  ---------------------------------------------------------
plt.figure()
plt.plot(np.array(reward["training"]))
# ------------------------------------------------------------------------------------------------------------
plt.title("rewards in training")
plt.savefig('./rewards_train.png', dpi=300)
plt.show()
# ------------------------------------------------------------------------------------------------------------

# Plot testing figures
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


# Plots from stable-baselines3

# Helper from the library
# results_plotter.plot_results([os.path.join(root_folder, experiment)], 1e5, results_plotter.X_TIMESTEPS, "Dynasim")

# plot_results(os.path.join(root_folder, experiment))

# plot_episodes(os.path.join(root_folder, experiment))