from ndfinance.strategies import Strategy, PeriodicRebalancingStrategy
from ndfinance.brokers.base import order

class SameWeightBuyHold(Strategy):
    def __init__(self):
        super(SameWeightBuyHold, self).__init__()
        self.ordered = False

    def _logic(self):
        if not self.ordered:
            weight = 1 / len(self.broker.assets)
            [self.broker.order(order.Weight(asset, self.broker.portfolio.portfolio_value, 1, weight))
             for asset in self.broker.assets.values()]
            self.ordered = True


class SameWeightBuynRebalance(PeriodicRebalancingStrategy):
    def __init__(self, rebalance_period):
        super(SameWeightBuynRebalance, self).__init__(rebalance_period)

    def register_engine(self, *args, **kwargs):
        super(SameWeightBuynRebalance, self).register_engine(*args, **kwargs)
        weight = 1 / len(self.broker.assets.keys())
        self.weights = [weight for _ in self.broker.assets.keys()] 
        return self

    def _logic(self):
        self.broker.order(order.Rebalance(tickers=self.broker.assets.keys(), weights=self.weights))
