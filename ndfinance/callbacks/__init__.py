import numpy as np


class Callback:
    def __init__(self):
        pass

    def __call__(self, *args, **kwargs):
        # implement main callback logic here
        raise NotImplementedError

    def register_engine(self, engine):
        self.engine = engine
        self.broker = self.engine.broker
        self.indexer = self.engine.broker.indexer
        self.data_provider = self.engine.broker.data_provider
        return self


from pprint import pprint

class PositionWeightPrinterCallback(Callback):
    def __init__(self):
        super(PositionWeightPrinterCallback, self).__init__()

    def __call__(self, *args, **kwargs):

        value = np.array([p.position_value for p in self.broker.portfolio.positions.values()])
        weight = value/value.sum()

        for k, w in zip(self.broker.portfolio.positions.keys(), weight):
            side = "sell" if self.broker.portfolio.positions[k].side == -1 else "buy"
            print(f"{k}:{np.round(w*100, 2)}%, side:{side}")

        print("\n")


