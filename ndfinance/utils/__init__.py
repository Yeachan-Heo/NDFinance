import random
import string
from ndfinance import OHLCVT
 
def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


class Universe(object):
    def __init__(self, broker=None, data_provider=None):
        self.broker = broker
        self.data_provider = data_provider

    def set_broker(self, broker):
        self.broker = broker
        self.data_provider = self.broker.data_provider

    def __call__(self):
        return self.broker.assets


class AvailableStockUniverse(Universe):
    def __init__(self, *args, **kwargs):
        super(AvailableStockUniverse, self).__init__(*args, **kwargs)

    def set_broker(self, *args, **kwargs):
        super(AvailableStockUniverse, self).__init__(*args, **kwargs)
        self.indexer = self.broker.indexer

    def __call__(self):
        return {self.broker.assets[ticker] 
            for ticker in self.broker.assets.keys() 
                if self.indexer.timestamp == self.data_provider.get_ohlcvt(
                    ticker, OHLCVT.timestamp)}


    