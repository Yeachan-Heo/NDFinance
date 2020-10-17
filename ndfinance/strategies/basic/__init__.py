from ndfinance.strategies import Strategy, PeriodicRebalancingStrategy
from ndfinance.brokers.base import order
from ndfinance.brokers.base.order import *
from ndfinance.strategies.utils import *


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


class OscillatorStrategy(Strategy):
    def __init__(self, breakout_threshold, oversold_threshold, overbought_threshold, osc_label, 
    use_short=False, use_time_cut=False, timecut_params=None, use_n_perc_rule=False, n_perc_params=None, 
    use_stop_loss=False, stop_loss_params=None, *args, **kwargs):
        super(OscillatorStrategy, self).__init__()
        self.use_short = use_short
        self.breakout_threshold = breakout_threshold
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.osc_label = osc_label
        
        self.use_time_cut = use_time_cut
        self.timecut_params = timecut_params
        
        self.use_n_perc_rule = use_n_perc_rule
        self.n_perc_params = n_perc_params
        
        self.use_stop_loss = use_stop_loss
        self.stop_loss_params = stop_loss_params

    def register_engine(self, *args, **kwargs):
        super(OscillatorStrategy, self).register_engine(*args, **kwargs)
        self.ticker = list(self.broker.assets.keys())[0]
        return self

    def _logic(self):
        indicator_ = self.data_provider.get_ohlcvt(self.ticker, self.osc_label, n=2)
        indicator = indicator_[-1]
        indicator_prev = indicator_[0]

        if not self.broker.portfolio.positions:
            ordered = True
            value = apply_n_percent_rule(self.broker.portfolio.portfolio_value, **self.n_perc_params) \
                if self.use_n_perc_rule else self.broker.portfolio.portfolio_value

            if (indicator >= self.breakout_threshold) & (indicator_prev < self.breakout_threshold):
                self.broker.order(Weight(self.broker.assets[self.ticker], value, 1, 1))
            elif (((indicator <= self.breakout_threshold) & (indicator_prev > self.breakout_threshold)) & self.use_short):
                self.broker.order(Weight(self.broker.assets[self.ticker], value, -1, 1))
            else:
                ordered = False
            
            if ordered & self.use_time_cut:
                self.broker.order(TimeCutClose(self.broker.assets[self.ticker], self.indexer.timestamp, **self.timecut_params))
            if ordered & self.use_stop_loss:
                self.broker.order(StopLoss(self.broker.assets[self.ticker], **self.stop_loss_params))


        elif self.broker.portfolio.positions[self.ticker].side == 1:
            if (indicator <= self.overbought_threshold) & (indicator_prev > self.overbought_threshold):
                self.broker.order(Close(self.broker.assets[self.ticker]))

        elif self.broker.portfolio.positions[self.ticker].side == -1:
            if (indicator >= self.oversold_threshold) & (indicator_prev < self.oversold_threshold):
                self.broker.order(Close(self.broker.assets[self.ticker]))
