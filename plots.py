import numpy as np
import matplotlib.pyplot as plt

# traces_filename = "/Users/paola/UA/dynamic_sim/python.traces"
traces_filename = "/home/darpa/dynamicsim/dynamicsim_ai/python.traces"
jobs_train = []  # jobs sent
ms_train = []  # ms deployed
cpu_usage_train = []
overflow_train = []
peak_latency_train = []
avg_latency_train = []
action_train = []

jobs_eval = []  # jobs sent
ms_eval = []  # ms deployed
cpu_usage_eval = []
overflow_eval = []
peak_latency_eval = []
avg_latency_eval = []
action_eval = []

timesteps = {}

act_2_meaning = {
    0: "increase",
    1: "decrease",
    2: "nothing"
}

with open(traces_filename) as f:
    mode = "training"
    for line in f:
        line = line.rstrip().split("|")[-1]
        if line.startswith("Mode"):
            mode = line.split(":")[-1].rstrip().split()[0]
            timesteps[mode] = int(line.split(":")[-1].rstrip().split()[-2])
        if line.startswith("Traffic"):
            if mode == "training":
                jobs_train.append(int(line.split(":")[-1].rstrip()))
            else:
                jobs_eval.append(int(line.split(":")[-1].rstrip()))
        if line.startswith("MS"):
            if mode == "training":
                ms_train.append(int(line.split(":")[-1].rstrip()))
            else:
                ms_eval.append(int(line.split(":")[-1].rstrip()))
        if line.startswith("Cpu"):
            if mode == "training":
                cpu_usage_train.append(float(line.split(":")[-1].rstrip()))
            else:
                cpu_usage_eval.append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Overflow"):
            if mode == "training":
                overflow_train.append(float(line.split(":")[-1].rstrip()))
            else:
                overflow_eval.append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Peak Latency"):
            if mode == "training":
                peak_latency_train.append(float(line.split(":")[-1].rstrip()))
            else:
                peak_latency_eval.append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Avg Latency"):
            if mode == "training":
                avg_latency_train.append(float(line.split(":")[-1].rstrip()))
            else:
                avg_latency_eval.append(float(line.split(":")[-1].rstrip()))
        if line.startswith("Action"):
            line = line.split(",")[0]
            if mode == "training":
                action_train.append(act_2_meaning[int(line.split(":")[-1].rstrip())])
            else:
                action_eval.append(act_2_meaning[int(line.split(":")[-1].rstrip())])

# jobs has 2000 elements while the rest have one element more, the first element can be discarded as it belongs to the first observation
jobs_train = np.asarray(jobs_train) / 300.
ms_train = ms_train[1:]
cpu_usage_train = cpu_usage_train[1:]
overflow_train = overflow_train[1:]
peak_latency_train = peak_latency_train[1:]
avg_latency_train = avg_latency_train[1:]
action_train = action_train[1:]

# jobs has 2000 elements while the rest have one element more, the first element can be discarded as it belongs to the first observation
jobs_eval = np.asarray(jobs_eval) / 300.
ms_eval = ms_eval[1:]
cpu_usage_eval = cpu_usage_eval[1:]
overflow_eval = overflow_eval[1:]
peak_latency_eval = peak_latency_eval[1:]
avg_latency_eval = avg_latency_eval[1:]
action_eval = action_eval[1:]

# Plot trainig figures
plt.figure()
plt.plot(jobs_train)
plt.title("workload in training")
plt.show()

plt.figure()
plt.plot(ms_train)
plt.title("number of ms in training")
plt.show()

plt.figure()
plt.plot(cpu_usage_train)
plt.title("cpu usage in training")
plt.show()

plt.figure()
plt.plot(cpu_usage_train)
plt.title("overflow in training")
plt.show()

plt.figure()
plt.plot(peak_latency_train)
plt.title("peak latency[sec] in training")
plt.show()

plt.figure()
plt.plot(avg_latency_train)
plt.title("avg latency[sec] in training")
plt.show()

plt.figure()
plt.plot(action_train, 'o')
plt.title("actions in training")
plt.show()

# Plot testing figures
plt.figure()
plt.plot(jobs_eval)
plt.title("workload in testing")
plt.show()

plt.figure()
plt.plot(ms_eval)
plt.title("number of ms in testing")
plt.show()

plt.figure()
plt.plot(cpu_usage_eval)
plt.title("cpu usage in testing")
plt.show()

plt.figure()
plt.plot(cpu_usage_eval)
plt.title("overflow in testing")
plt.show()

plt.figure()
plt.plot(peak_latency_eval)
plt.title("peak latency[sec] in testing")
plt.show()

plt.figure()
plt.plot(avg_latency_eval)
plt.title("avg latency[sec] in testing")
plt.show()

plt.figure()
plt.plot(action_eval, 'o')
plt.title("actions in testing")
plt.show()
