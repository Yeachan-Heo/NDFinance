import pandas as pd
import numpy as np
import datetime
import numba
import time
import os


def cummul(array):
    temp = 1
    ret = []
    for element in array:
        temp *= element
        ret.append(temp)
    return np.array(ret)

def listdirs(folder):
    return [
        d for d in (os.path.join(folder, d1) for d1 in os.listdir(folder))
        if os.path.isdir(d)
    ]

def split_list(alist, wanted_parts=1, slip=2):
    length = len(alist)
    return [ alist[int(np.clip(i*length// wanted_parts-slip, 0, np.inf)): (i+1)*length // wanted_parts]
             for i in range(wanted_parts) ]


def to_timestamp(timestamp, pattern="%Y-%m-%d %H:%M:%S"):
    return np.array([time.mktime(datetime.datetime.strptime(t, pattern).timetuple()) for t in
     timestamp.tolist()], dtype=np.float64)

def to_datetime(timestamp):
    return [datetime.datetime.fromtimestamp(x) for x in timestamp]

def sign(a):
    return (a > 0) - (a < 0)

def fillna_arr(array, **kwargs):
    df = pd.DataFrame({"v": array})
    df = df.fillna(**kwargs)
    return df["v"].values


def rolling_window(observations, n, func:lambda x: x):
    ret = []
    for i, data in enumerate(observations[n - 1:]):
        strip = func(observations[i:i + n])
        ret.append(strip)
    return np.array(ret)


def get_rolling_window_size(timestamp_lst, period):
    return len(timestamp_lst[np.where(timestamp_lst <= timestamp_lst[0] + period)[0]])

def filter_array(func, array):
    mask = func(array)
    index = np.where(mask)[-1]
    return array[index]

def append_dict(d, d1):
    for key, value in d1.items():
        d[key] = value

class LabeledScalarStorage:
    def __init__(self, *args):
        self.value = {}
        for a in args:
            self.add_label(a)

    def __add__(self, other):
        for key, value in other.value.items():
            self.value[key] = value
        return self

    def __getitem__(self, item):
        return self.value[item]

    def __setitem__(self, key, value):
        self.value[key] = value

    def keys(self):
        return self.value.keys()

    def values(self):
        return self.value.values()

    def items(self):
        return self.value.items()

    def add_label(self, label):
        self.value[label] = []

    def add_scalar(self, label, scalar):
        self.value[label].append(scalar)

    def extend(self, other):
        for key in self.value.keys():
            self[key].extend(other[key])

    @property
    def dataframe(self):
        return pd.DataFrame(self.value)

class StructureDataset:
    def __init__(self):
        self.value = {}

    def __getitem__(self, item):
        return self.value[item]

    def __setitem__(self, x, y):
        if isinstance(self.value[x], StructureDataset):
            raise ValueError("can't __setitem__ to group")
        self.value[x] = y

    def keys(self):
        return self.value.keys()

    def values(self):
        return self.value.values()

    def items(self):
        return self.value.items()

    def create_group(self, name):
        self.value[name] = StructureDataset()
        return self.value[name]

    def create_dataset(self, name, data):
        self.value[name] = np.array(data)

    def get(self, *args):
        temp = self
        for a in args:
            temp = temp[a]
        return temp

