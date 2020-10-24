from ndfinance.core import BacktestEngine
from ndfinance.strategies.utils import *


class Strategy:
    def __init__(self):
        pass

    def _logic(self):
        raise NotImplementedError

    def logic(self):
        self.universe = self._universe()
        self._logic()

    def init_universe(self):
        self._universe = Universe()

    def register_engine(self, engine):
        self.engine: BacktestEngine = engine
        self.broker = self.engine.broker
        self.indexer = self.engine.indexer
        self.data_provider = self.engine.data_provider
        self.init_universe()
        self._universe.set_broker(self.broker)
        return self


class PeriodicRebalancingStrategy(Strategy):
    def __init__(self, rebalance_period):
        super(PeriodicRebalancingStrategy, self).__init__()
        self.rebalance_period = rebalance_period

    def init_universe(self):
        self._universe = AvailableStockUniverse()

    def register_engine(self, *args, **kwargs):
        super(PeriodicRebalancingStrategy, self).register_engine(*args, **kwargs)
        self.last_rebalance = self.indexer.timestamp
        return self

    def logic(self):
        if (self.indexer.timestamp - self.last_rebalance) >= self.rebalance_period:
            super(PeriodicRebalancingStrategy, self).logic()
            self.last_rebalance = self.indexer.timestamp
        