from ndfinance.strategies import PeriodicRebalancingStrategy
from ndfinance.strategies.utils import apply_n_percent_rule
from ndfinance import Weight, Close
import numpy as np
from pprint import pprint as print

class ActualMomentumStratagy(PeriodicRebalancingStrategy):
    def __init__(self, momentum_threshold, rebalance_period, momentum_label="momentum", momentum_timeframe=None, clip_param=0.3):
        super(ActualMomentumStratagy, self).__init__(rebalance_period)
        self.momentum_threshold = momentum_threshold
        self.momentum_label = momentum_label
        self.momentum_timeframe = momentum_timeframe
        self.clip_param = clip_param

    def register_engine(self, *args, **kwargs):
        super(ActualMomentumStratagy, self).register_engine(*args, **kwargs)
        if self.momentum_timeframe is None:
            self.momentum_timeframe = self.data_provider.primary_timeframe
        return self

    def _logic(self):
        momentum = {
            ticker : self.data_provider.get_ohlcvt(
                ticker, self.momentum_label, self.momentum_timeframe)[-1]
            for ticker in self.broker.assets.keys()
        }

        momentum_dict = {ticker : (m if np.abs(m) >= self.momentum_threshold else 0) for ticker, m in momentum.items()}
        momentum_values = np.array(list(momentum_dict.values()))
        
        momentum_values = np.clip(
            momentum_values, 
            momentum_values.mean()-momentum_values.std()*self.clip_param, 
            momentum_values.mean()+momentum_values.std()*self.clip_param
        )
        if np.abs(momentum_values).sum() == 0:
            momentum_values += 1e+10
            
        weight = momentum_values / np.abs(momentum_values).sum()
        side = (weight > 0).astype(int) * 2 - 1

        for weight, side, ticker in sorted(zip(np.abs(weight), side, self.broker.assets.keys())):
            if ticker in self.broker.portfolio.positions.keys():
                if weight == 0:
                    self.broker.order(Close(self.broker.assets[ticker]))
                    continue
                self.broker.order(
                    Weight(self.broker.assets[ticker], (self.broker.portfolio.portfolio_value_total), side, np.abs(weight)))
                continue
            self.broker.order(
                    Weight(self.broker.assets[ticker], (self.broker.portfolio.portfolio_value_total), side, np.abs(weight)))
                
