import datetime
import pandas as pd
import numpy as np
import datetime
import time

import tqdm

from blqt.backtest.utils import *

from numba import jit, jitclass

class TimeIndexer(object):
    def __init__(self, timestamp_lst, from_timestamp=-np.inf, to_timestamp=np.inf):
        self.timestamp = None

        self.timestamp_lst =timestamp_lst[np.where(
            (from_timestamp <= timestamp_lst) & (timestamp_lst <= to_timestamp))[0]]

        self.idx = -1
        self.lastidx = len(self.timestamp_lst)
        self.first_timestamp = self.timestamp_lst[0]
        self.last_timestamp = self.timestamp_lst[-1]
        self.move()

    def move(self):
        self.idx += 1
        self.timestamp = self.timestamp_lst[self.idx]

    def is_done(self):
        return self.idx == self.lastidx
        
    @property
    def datetime(self):
        return datetime.datetime.fromtimestamp(self.timestamp)


class FinancialProduct:
    def __init__(self, ticker, tick_size, tick_value, slippage, min_margin_rate, maintenance_margin_rate, min_amount):
        self.ticker = ticker

        self.tick_size = np.array(tick_size)
        self.tick_value = np.array(tick_value)

        self.slippage = np.array(slippage)

        self.min_margin_rate = np.array(min_margin_rate)
        self.maintenance_margin_rate = np.array(maintenance_margin_rate)

        self.min_amount = np.array(min_amount)


class PositionLog:
    def __init__(self, amount, timestamp):
        self.timestamp = timestamp
        self.order_direction = np.sign(amount)

class Position:
    def __init__(self, product, amount, avg_price, timestamp):
        self.product:FinancialProduct = product
        self.amount = amount
        self.avg_price = avg_price
        self.log = []
        self.log.append(PositionLog(amount, timestamp))

    def add(self, amount, avg_price, timestamp):
        new_amount = self.amount + amount
        sign_is_same = np.sign(amount) == np.sign(self.amount)

        self.log.append(PositionLog(amount, timestamp))

        if sign_is_same:
            self.avg_price = (self.amount * self.avg_price + amount * avg_price) / new_amount
            self.amount = new_amount
            return 0

        if not sign_is_same:
            realized_pnl = self.unrealized_pnl * np.clip(np.abs(amount / self.amount), a_max = 1, a_min = 0)
            self.avg_price = avg_price if np.abs(amount) > np.abs(self.amount) else self.avg_price
            self.amount = new_amount
            return realized_pnl

    def update_value(self, current_price):
        self.unrealized_pnl = (current_price - self.avg_price) // self.product.tick_size * self.product.tick_value * self.amount
        self.unrealized_pnl_rate = (current_price / self.avg_price - 1) * np.sign(self.amount)
        self.position_value = current_price // self.product.tick_size * self.product.tick_value * self.amount

    def update_weight(self, pv):
        self.weight = self.position_value / pv



class System:
    def __init__(self, use_tqdm=False, name="backtest_result"):
        self.logger = None
        self.broker = None
        self.data_provider = None
        self.stratagy = None
        self.use_tqdm=use_tqdm
        self.name = name

    def set_stratagy(self, stratagy):
        self.stratagy = stratagy
        self.stratagy.set_system(self)

    def set_broker(self, broker):
        self.broker = broker

    def set_data_provider(self, data_provider):
        self.data_provider = data_provider

    def set_logger(self, logger):
        self.logger = logger
        self.logger.set_system(self)

    def main_loop(self):
        raise NotImplementedError

    def result(self):
        result = self.logger.result()
        print(result)

        with open(self.name + ".txt", "w") as f:
            f.write(result)

    def plot(self):
        self.logger.plot_relative()


class BacktestSystem(System):
    def __init__(self, desc="Main", name="backtest_result"):
        super(BacktestSystem, self).__init__(name=name)
        self.desc = desc

    def run_step(self):
        self.broker.indexer.move()
        self.broker.calc_pv()
        self.broker.update_weight()
        self.stratagy.logic()
        self.logger.log()

    def run(self):
        for _ in tqdm.tqdm(range(self.broker.indexer.lastidx-1), desc=self.desc):
            self.run_step()
        return self.logger

import multiprocessing
import copy
from blqt.backtest.loggers import BasicLogger


class DistributedBacktestSystem():
    def __init__(self, n_cores=4, name="backtest_result"):
        super(DistributedBacktestSystem, self).__init__()
        self.n_cores = n_cores
        self.name = name

    def set_broker(self, broker):
        self.broker = broker
        self.margin = self.broker.margin

    def set_stratagy(self, stratagy):
        self.stratagy = stratagy

    def set_logger(self, logger):
        self.logger = logger

    def set_data_provider(self, data_provider):
        self.data_provider = data_provider

    def run_distributed(self):
        timestamps = []
        n = len(self.broker.indexer.timestamp_lst) // self.n_cores

        for i in range(self.n_cores):
            timestamp_lst = self.broker.indexer.timestamp_lst[int(np.clip(i*n-2, 0, np.inf)):(i+1)*n]
            timestamps.append(timestamp_lst)

        systems = []

        for i, timestamp_lst in enumerate(timestamps):
            indexer = TimeIndexer(timestamp_lst)
            data_provider = copy.deepcopy(self.data_provider)
            data_provider.register_time_indexer(indexer)

            data_provider.lock_data()

            broker = copy.deepcopy(self.broker)
            broker.data_provider = data_provider
            broker.indexer = indexer

            stratagy = copy.deepcopy(self.stratagy)
            logger = copy.deepcopy(self.logger)



            system = BacktestSystem(f"#{i:02d}")

            system.set_broker(broker)
            system.set_data_provider(data_provider)
            system.set_stratagy(stratagy)
            system.set_logger(logger)

            systems.append(system)

        p = multiprocessing.Pool(self.n_cores)

        loggers = p.map(BacktestSystem.run, systems)

        change_perc = []
        pv_lst = []
        trade_hist = []
        trade_hist_rate = []
        timestamp_lst = []
        benchmark_lst = []


        for logger in loggers:
            logger._result()
            change_perc_per_timeframe = [1]
            change_perc_per_timeframe.extend(logger.pv_lst[1:] / logger.pv_lst[:-1])

            change_perc.extend(change_perc_per_timeframe)
            trade_hist.extend(logger.trade_hist)
            trade_hist_rate.extend(logger.trade_hist_rate)
            timestamp_lst.extend(logger.timestamp_lst)
            benchmark_lst.extend(logger.benchmark_lst)

        df = pd.DataFrame({
            "benchmark": benchmark_lst,
            "timestamp" : timestamp_lst,
            "change" : change_perc
        })

        df = df.iloc[df["timestamp"].drop_duplicates().index]

        pv = self.margin

        for change in df["change"].values:
            pv *= change
            pv_lst.append(pv)


        new_logger = BasicLogger("")
        new_logger.pv_lst = pv_lst
        new_logger.benchmark_lst = df["benchmark"].values
        new_logger.timestamp_lst = df["timestamp"].values
        new_logger.trade_hist = trade_hist
        new_logger.trade_hist_rate = trade_hist_rate

        self.new_logger = new_logger

    def run(self):
        self.run_distributed()

    def result(self):
        result = self.new_logger.result()
        print(result)

        with open(self.name + ".txt", "w") as f:
            f.write(result)

    def plot(self):
        self.new_logger.plot_relative()


class TimeFrames:
    Minute = 60
    Second = 1
    Hour = Minute * 60
    Day = Hour * 24
    Week = Day * 7



