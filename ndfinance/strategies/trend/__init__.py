from ndfinance.strategies import PeriodicRebalancingStrategy

class ActualMomentumStratagy(PeriodicRebalancingStrategy):
    def __init__(self, momentum_threshold, rebalance_period):
        super(ActualMomentumStratagy, self).__init__(rebalance_period)
        