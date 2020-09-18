from blqt.backtest.brokers import Broker, BackTestBroker
from blqt.backtest.base import *
import numpy as np
import datetime

class Stratagy:
    def __init__(self):
        self.sys = None

    def set_system(self, system):
        self.sys = system
        self.broker = system.broker
        self.data_provider = system.data_provider
        self.logger = self.sys.logger

    def logic(self):
        raise NotImplementedError


class TimeCutStratagyBase(Stratagy):
    def __init__(self, ticker="Ticker", timecut=TimeFrames.Hour):
        super(TimeCutStratagyBase, self).__init__()
        self.side, self.weight = 0, 0
        self.ticker = ticker
        self.timecut = timecut

    def update_side_and_weight(self):
        raise NotImplementedError

    def logic(self):
        self.update_side_and_weight()

        if self.weight == 0:
            return

        if self.broker.positions:
            if (self.broker.indexer.timestamp - self.broker.positions["Ticker"]) >= self.timecut:
                self.broker.close_position(self.ticker)
        else:
            self.broker.order_target_weight_pv(self.ticker, weight=self.weight * self.side)

