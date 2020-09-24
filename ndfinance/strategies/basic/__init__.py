from ndfinance.strategies import Strategy
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
