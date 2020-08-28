import pandas as pd
import numpy as np
import quandl
from typing import *


class TimeIndexedData(object):
    def __init__(self):
        self.array:Optional[np.ndarray] = None
        self.labels = {}

    def add_array(self, label, array):
        self.labels[label] = len(self.labels.values())
        self.array = array if isinstance(self.array, type(None)) else np.vstack((self.array, array))

    def from_pandas(self, df:pd.DataFrame):
        for label in df.columns:
            self.add_array(label, df[label].values)

    def from_quandl(self, *args, **kwargs):
        data = quandl.get(*args, **kwargs)
        data.columns = [x.lower() for x in data.columns]
        self.from_pandas(data)

    def add_ta(self, func, label, *args, **kwargs):
        func_args = {key:self[key] for key in args}
        func_args.update(kwargs)
        self.add_array(label, func(**func_args))

    def __getitem__(self, item):
        return self.array[self.labels[item]]

