from blqt.backtest.stratagies import Stratagy, TimeFrames
from blqt.backtest.stratagies import *
import numpy as np
class SameWeightBuyAndHold(Stratagy):
    def __init__(self, rebalance_period=60*60*24*7, benchmark_ticker="^KS11"):
        super(SameWeightBuyAndHold, self).__init__()
        self.broker : BackTestBroker
        self.last_rebalanced = -np.inf
        self.rebalance_period = rebalance_period
        self.benchmark_ticker = benchmark_ticker

    def logic(self):
        if (self.broker.indexer.timestamp - self.last_rebalanced) > self.rebalance_period:
            n_tickers = len(self.broker.tickers.keys())-1
            weight = 1 / n_tickers
            for ticker in self.broker.tickers.keys():
                if ticker == self.benchmark_ticker:
                    continue
                self.broker.order_target_weight_pv(ticker, weight)
            self.last_rebalanced = self.broker.indexer.timestamp