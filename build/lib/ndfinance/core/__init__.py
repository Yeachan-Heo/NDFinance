import ray
import tqdm
from ndfinance.brokers.backtest import BacktestBroker, TimeIndexer, BacktestDataProvider


class Engine:
    def __init__(self):
        pass


class BacktestEngine(Engine):
    def __init__(self, use_tqdm=True, desc="main"):
        super(BacktestEngine, self).__init__()
        self.use_tqdm = use_tqdm
        self.desc = desc
        self.broker_available = False
        self.callback = lambda : None

    def register_broker(self, broker:BacktestBroker):
        self.broker: BacktestBroker = broker
        self.indexer: TimeIndexer = self.broker.indexer
        self.data_provider: BacktestDataProvider = self.broker.data_provider
        self.broker_available = True

    def register_strategy(self, strategy):
        assert self.broker_available, "set broker first"
        self.strategy = strategy.register_engine(self)

    def register_callback(self, callback):
        assert self.broker_available, "set broker first"
        self.callback = callback.register_engine(self)

    def run(self):
        self.indexer.move()
        if self.use_tqdm:
            for _ in tqdm.tqdm(range(self.indexer.lastidx - 2), desc=self.desc):
                self.broker.portfolio.update_portfolio_value()
                self.strategy.logic()
                self.indexer.move()
                self.broker.run_queue()
                self.callback()
        else:
            for _ in range(self.indexer.lastidx - 2):
                self.broker.portfolio.update_portfolio_value()
                self.strategy.logic()
                self.indexer.move()
                self.broker.run_queue()
                self.callback()

        return self.broker.get_log()


class MultiStrategyBackrestEngine(BacktestEngine):
    def __init__(self, *args, **kwargs):
        super(MultiStrategyBackrestEngine, self).__init__(*args, **kwargs)
        self.strategies = []
        self.callbacks = []

    def register_strategies(self, *strategies):
        [self.strategies.append(s.set_engine(self)) for s in strategies]

    def register_callbacks(self, *callbacks):
        [self.callbacks.append(s.set_engine(self)) for s in callbacks]

    def run(self):
        self.indexer.move()
        if self.use_tqdm:
            for _ in tqdm.tqdm(range(self.indexer.lastidx - 2), desc=self.desc):
                self.broker.portfolio.update_portfolio_value()
                [strategy.logic() for strategy in self.strategies]
                self.indexer.move()
                self.broker.run_queue()
                [callback() for callback in self.callbacks]
        else:
            for _ in range(self.indexer.lastidx - 2):
                self.broker.portfolio.update_portfolio_value()
                [strategy.logic() for strategy in self.strategies]
                self.strategy.logic()
                self.indexer.move()
                self.broker.run_queue()
                [callback() for callback in self.callbacks]

        return self.broker.get_log()





