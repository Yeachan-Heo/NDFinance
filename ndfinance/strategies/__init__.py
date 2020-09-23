from ndfinance.core import BacktestEngine

class Strategy:
    def __init__(self):
        pass

    def logic(self):
        raise NotImplementedError

    def register_engine(self, engine):
        self.engine: BacktestEngine = engine
        self.broker = self.engine.broker
        self.indexer = self.engine.indexer
        self.data_provider = self.engine.data_provider
        return self
