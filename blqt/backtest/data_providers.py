import numpy as np
from blqt.backtest.historical_data import TimeIndexedData
from blqt.backtest.base import TimeIndexer
from typing import *


class DataProvider(object):
    def __init__(self, *args, **kwargs):
        pass

    def current(self, *args, **kwargs) -> np.ndarray:
        return np.ndarray([])

    def historical(self, *args, **kwargs) -> np.ndarray:
        return np.ndarray([])

    def fundamental(self, *args, **kwargs) -> np.ndarray:
        return np.ndarray([])

    def fundamental_historical(self, *args, **kwargs) -> np.ndarray:
        return np.ndarray([])

class BacktestDataProvider(DataProvider):
    def __init__(self, *args, **kwargs):
        super(BacktestDataProvider, self).__init__(*args, **kwargs)
        self.timeindexer = None
        self.ohlcv_data = {}
        self.fundamental_data = {}

    def register_time_indexer(self, indexer):
        self.timeindexer = indexer

    def register_ohlcv_data(self, ticker, data, timeframe=-1):
        if not ticker in self.ohlcv_data.keys():
            self.ohlcv_data[ticker] = {}
        self.ohlcv_data[ticker][timeframe] : TimeIndexedData = data

    def register_fundamental_data(self, ticker, data, timeframe=-1):
        if not ticker in self.fundamental_data.keys():
            self.fundamental_data[ticker] = {}
        self.fundamental_data[ticker][timeframe] : TimeIndexedData = data

    def current(self, ticker:str, label:str, timeframe=None, *args, **kwargs) -> np.ndarray:
        hist = self.historical(ticker, label, timeframe)
        return hist[-1]

    def historical(self, ticker:str, label:str, timeframe=None, *args, **kwargs) -> np.ndarray:
        if timeframe is None:
            timeframe = min(self.ohlcv_data[ticker].keys())

        index = np.where(
            self.ohlcv_data[ticker][timeframe]["timestamp"] <= self.timeindexer.timestamp)[-1]

        return self.ohlcv_data[ticker][timeframe][label][index]

    def add_benchmark(self, data):
        self.benchmark_data = data

    def get_benchmark_current(self, label="close"):
        index = np.where(
            self.benchmark_data["timestamp"] <= self.timeindexer.timestamp)[-1][-1]
        return self.benchmark_data[label][:index]

    def lock_data(self):
        for ticker, dic1 in self.ohlcv_data.items():
            for timeframe, data in dic1.items():
                data : TimeIndexedData
                from_index = np.where(
                    self.timeindexer.first_timestamp<=data["timestamp"])[0][0]
                to_index = np.where(
                    self.timeindexer.last_timestamp>=data["timestamp"])[-1][-1]
                index = np.arange(int(np.clip(from_index-1, 0, np.inf)), to_index)
                data.array = data.array[:, index]



