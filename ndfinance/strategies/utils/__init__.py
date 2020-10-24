import numpy as np
from ndfinance.brokers.base import OHLCVT

def apply_n_percent_rule(value, n_percent=5, loss_cut_percent=20):
    return (value * n_percent / 100) / (loss_cut_percent / 100)


class Universe(object):
    def __init__(self, broker=None, data_provider=None):
        self.broker = broker
        self.data_provider = data_provider

    def set_broker(self, broker):
        self.broker = broker
        self.data_provider = broker.data_provider

    def __call__(self):
        return self.broker.assets


class AvailableStockUniverse(Universe):
    def __init__(self, *args, **kwargs):
        super(AvailableStockUniverse, self).__init__(*args, **kwargs)

    def set_broker(self, *args, **kwargs):
        super(AvailableStockUniverse, self).__init__(*args, **kwargs)
        self.indexer = self.broker.indexer

    def __call__(self):
        ret = {}
        for ticker in self.broker.assets.keys():
            timestamp = self.broker.data_provider.get_ohlcvt_current(ticker, OHLCVT.timestamp)
            if timestamp is None: continue
            ret[ticker] = self.broker.assets[ticker]
        return ret

