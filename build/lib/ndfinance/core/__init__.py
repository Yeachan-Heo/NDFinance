import ray
import tqdm
from copy import deepcopy
from ndfinance.brokers.backtest import *
from ndfinance.utils.array_utils import *
import sys
import time
from functools import reduce

class Engine:
    def __init__(self):
        pass




class BacktestEngine(Engine):
    def __init__(self, use_tqdm=True, desc="[ENGINE]"):
        super(BacktestEngine, self).__init__()
        self.use_tqdm = use_tqdm
        self.desc = desc
        self.broker_available = False
        self.callback = lambda : None
        self.cnt = 0

    def register_broker(self, broker:BacktestBroker):
        self.broker: BacktestBroker = broker
        self.indexer: TimeIndexer = self.broker.indexer
        self.data_provider: BacktestDataProvider = self.broker.data_provider
        self.data_provider.set_indexer(self.broker.indexer)
        #print(self.data_provider.group_ohlcv.keys, self.broker.indexer)
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
                self.cnt += 1

        return self.broker.get_log()
    
    def get_cnt(self):
        return self.cnt


BacktestEngineWorker = ray.remote(BacktestEngine)

class DistributedBacktestEngine(BacktestEngine):
    def __init__(self, n_cores, chunk_size=TimeFrames.day, *args, **kwargs):
        super(DistributedBacktestEngine, self).__init__(*args, **kwargs)
        self.engines = []
        self.n_cores = n_cores
    
    def distribute(self):
        ray.init()
        t = time.time()
        print("-"*50, "[ENGINE DISTRIBUTION START]", "-"*50)

        chunks = self.indexer.to_chunks(n_chunks = self.n_cores)
        indexers = [TimeIndexer(c) for c in chunks]
        data_providers = [deepcopy(self.data_provider) for _ in range(self.n_cores)]
        
        [dp.set_indexer(indexer) for dp, indexer in zip(data_providers, indexers)]
        [dp.cut_data() for dp in data_providers]
        brokers = [BacktestBroker(dp, self.broker.withdraw_config, self.broker.portfolio.initial_margin)
        for dp in data_providers]
        
        [broker.add_asset(*self.broker.assets.values()) for broker in brokers]
        
        self.engines = [BacktestEngineWorker.remote(use_tqdm=self.use_tqdm, desc=f"[ENGINE THREAD] #{'{:02d}'.format(i)}") for i in range(self.n_cores)]
        [e.register_broker.remote(broker) for e, broker in zip(self.engines, brokers)]
        [e.register_strategy.remote(deepcopy(self.strategy)) for e in self.engines]
        
        print("-"*50, f"[DISTRIBUTED {self.n_cores} ENGINES in {round(time.time()-t, 2)}s]", "-"*50)

    def run(self):
        out = [e.run.remote() for e in self.engines]
        temp = 0

        logs = [ray.get(o) for o in out]


        
        deltas = [list(np.array(log[PortFolioLogLabel.portfolio_value][1:])
         / np.array(log[PortFolioLogLabel.portfolio_value][:-1])) for log in logs]
        deltas = reduce(lambda x, y: x + y, deltas)
        deltas = [1] + deltas

        log = logs[0]

        for l in logs[1:]:
            for key, item in l.items():
                l[key] = item[1:]
            log.extend(l)

        log[PortFolioLogLabel.portfolio_value_total] = cummul(np.array(deltas)) * self.broker.portfolio.initial_margin
        log[PortFolioLogLabel.portfolio_value] = log[PortFolioLogLabel.portfolio_value_total]
        return log
        

        
class MultiStrategyBacktestEngine(BacktestEngine):
    def __init__(self, *args, **kwargs):
        super(MultiStrategyBacktestEngine, self).__init__(*args, **kwargs)
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





