import matplotlib.pyplot as plt
import json
import numpy as np

# with open('test.json') as f:
#     timings = dict(json.load(f))
#
# x = list(timings.keys())
# x = [int(i) for i in x]
#
# y = list(timings.values())
#
# plt.plot(y[1:])
# plt.xticks(np.arange(0, 8000, 1000))
# plt.show()

test = [1,2,3,4,5,6]
total = 0
[sum(value) for value in test]
print([total += value for value in test])