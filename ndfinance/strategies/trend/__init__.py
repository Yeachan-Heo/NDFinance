from ndfinance.strategies import PeriodicRebalancingStrategy, Strategy
from ndfinance.strategies.utils import apply_n_percent_rule
from ndfinance import Weight, Close, TimeFrames, Rebalance
import numpy as np
from pprint import pprint as print

class ActualMomentumStratagy(PeriodicRebalancingStrategy):
    def __init__(self, momentum_threshold, rebalance_period, n_pos=5, momentum_label="momentum", momentum_timeframe=None, clip_param=0.3):
        super(ActualMomentumStratagy, self).__init__(rebalance_period)
        self.momentum_threshold = momentum_threshold
        self.momentum_label = momentum_label
        self.momentum_timeframe = momentum_timeframe
        self.clip_param = clip_param
        self.n_pos = n_pos

    def register_engine(self, *args, **kwargs):
        super(ActualMomentumStratagy, self).register_engine(*args, **kwargs)
        if self.momentum_timeframe is None:
            self.momentum_timeframe = self.data_provider.primary_timeframe
        return self

    def _logic(self):
        momentum = {
            ticker : self.data_provider.get_ohlcvt(
                ticker, self.momentum_label, self.momentum_timeframe)[-1]
            for ticker in self.universe
        }

        momentum_dict = {ticker : momentum[ticker]
            for ticker in sorted(momentum, key=lambda x: momentum[x], reverse=True)[:5] if momentum[ticker] >= self.momentum_threshold}
        
        sum_momentum = sum(list(momentum_dict.values()))
        coeff = len(momentum_dict.keys()) / self.n_pos
        
        momentum_dict = {ticker : momentum[ticker] / sum_momentum * coeff for ticker in momentum_dict.keys()}

        self.broker.order(Rebalance(tickers=list(momentum_dict.keys()), weights=list(momentum_dict.values()), normalize=False))


class VolatilityBreakout(Strategy):
    def __init__(self, k=0.6, time_cut=9, max_positions=5, range_label="range", 
                range_timeframe=TimeFrames.day, main_timeframe=TimeFrames.hour):
        super(VolatilityBreakout, self).__init__()
        self.RANGE = "range"
        self.k = k
        self.time_cut = time_cut
        self.range_label = range_label
        self.max_positions = max_positions
        self.dict_ = {}

    def update_filtering_bet(self, ticker):
        return 1, 1

    def _update_params(self, ticker):
        filtering, bet = self.update_filtering_bet(ticker)
        dict_ = {
            self.RANGE : self.data_provider.get_ohlcvt(self.range_label),
        }
        return dict_

        

    
        
        
        

