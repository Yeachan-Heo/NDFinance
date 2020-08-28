from blqt.backtest.brokers import Broker, BackTestBroker
from blqt.backtest.base import *
import numpy as np
import datetime

class Stratagy:
    def __init__(self):
        self.sys = None

    def set_system(self, system):
        self.sys = system
        self.broker = system.broker
        self.data_provider = system.data_provider
        self.logger = self.sys.logger

    def logic(self):
        raise NotImplementedError


class SameWeightBuyAndHold(Stratagy):
    def __init__(self, rebalance_period=60*60*24*7, benchmark_ticker="^KS11"):
        super(SameWeightBuyAndHold, self).__init__()
        self.broker : BackTestBroker
        self.last_rebalanced = -np.inf
        self.rebalance_period = rebalance_period
        self.benchmark_ticker = benchmark_ticker

    def logic(self):
        if (self.broker.indexer.timestamp - self.last_rebalanced) > self.rebalance_period:
            n_tickers = len(self.broker.tickers.keys())-1
            weight = 1 / n_tickers
            for ticker in self.broker.tickers.keys():
                if ticker == self.benchmark_ticker:
                    continue
                self.broker.order_target_weight_pv(ticker, weight)
            self.last_rebalanced = self.broker.indexer.timestamp

class ActualMomentumStratagy(Stratagy):
    def __init__(self, rebalance_period=60*60*24*14, benchmark_ticker="^KS11", leverage=1):
        super(ActualMomentumStratagy, self).__init__()
        self.broker : BackTestBroker
        self.last_rebalanced = -np.inf
        self.rebalance_period = rebalance_period
        self.benchmark_ticker = benchmark_ticker
        self.leverage = leverage

    def logic(self):
        if (self.broker.indexer.timestamp - self.last_rebalanced) > self.rebalance_period:
            momentum_lst = []
            for ticker in self.broker.tickers.keys():
                if ticker == self.benchmark_ticker:
                    momentum_lst.append(-1)
                    continue
                momentum = self.data_provider.current(ticker, "momentum")
                momentum_lst.append(momentum)

            weight = np.sum(list(filter(lambda x: x > 0, momentum_lst)))

            for ticker, momentum in zip(self.broker.tickers.keys(), momentum_lst):
                if momentum > 0:
                    self.broker.order_target_weight_pv(ticker, momentum/weight*self.leverage)
                else:
                    if ticker in self.broker.positions.keys():
                        self.broker.close_position(ticker)

            self.last_rebalanced = self.broker.indexer.timestamp


class ActualMomentumStratagyLongShort(Stratagy):
    def __init__(self, rebalance_period=60*60*24, benchmark_ticker="^KS11", leverage=1, n=5):
        super(ActualMomentumStratagyLongShort, self).__init__()
        self.broker : BackTestBroker
        self.last_rebalanced = -np.inf
        self.rebalance_period = rebalance_period
        self.benchmark_ticker = benchmark_ticker
        self.leverage = leverage

    def logic(self):
        if (self.broker.indexer.timestamp - self.last_rebalanced) > self.rebalance_period:
            momentum_lst = []
            for ticker in self.broker.tickers.keys():
                if ticker == self.benchmark_ticker:
                    momentum_lst.append(-1)
                    continue
                momentum = self.data_provider.current(ticker, "momentum")
                momentum_lst.append(momentum)

            momentum_lst = zip(self.broker.tickers.keys())


            for ticker, momentum in zip(self.broker.tickers.keys(), momentum_lst):
                if momentum > 0:
                    self.broker.order_market(ticker, self.leverage)
                elif momentum < 0:
                    self.broker.order_market(ticker, -self.leverage)

            self.last_rebalanced = self.broker.indexer.timestamp


class SmaCrossInvTrend(Stratagy):
    def __init__(self, rebalance_period=60*60*24):
        super(SmaCrossInvTrend, self).__init__()
        self.rebalance_period = rebalance_period
        self.last_rebalanced = -np.inf

    def logic(self):
        tobuy = []
        toshort = []
        if (self.broker.indexer.timestamp - self.last_rebalanced) > self.rebalance_period:
            for ticker in self.broker.tickers.keys():
                MA200 = self.data_provider.current(ticker, "MA200")
                MA50 = self.data_provider.current(ticker, "MA50")



            self.last_rebalanced = self.broker.indexer.timestamp




class VBSingleCoin(Stratagy):
    def __init__(self, ticker, k, leverage=1):
        super(VBSingleCoin, self).__init__()
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.ticker = ticker
        self.k = k
        self.leverage = leverage
        self.range = np.nan

    def set_system(self, system):
        super(VBSingleCoin, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day
        if day != self.prev_day:
            self.prev_day = day
            self.range = self.curr_high - self.curr_low
            self.curr_start = self.data_provider.current(self.ticker, "open")
            self.curr_low, self.curr_high = np.inf, 0

        high, low = self.data_provider.current(self.ticker, "high"), self.data_provider.current(self.ticker, "low")

        if self.curr_high < high : self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            if (self.curr_start + self.k * self.range) <= self.curr_high:
                self.broker.order_target_weight_pv(self.ticker, self.leverage, price=high)
        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions[self.ticker].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(self.ticker, price=self.broker.data_provider.current(self.ticker, "open"))


class VBSingleCoinActualMomentumFiltered(Stratagy):
    def __init__(self, ticker, k, leverage=1):
        super(VBSingleCoinActualMomentumFiltered, self).__init__()
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.ticker = ticker
        self.k = k
        self.leverage = leverage
        self.range = np.nan

    def set_system(self, system):
        super(VBSingleCoinActualMomentumFiltered, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day
        if day != self.prev_day:
            self.prev_day = day
            self.range = self.curr_high - self.curr_low
            self.curr_start = self.data_provider.current(self.ticker, "open")
            self.curr_low, self.curr_high = np.inf, 0

        high, low = self.data_provider.current(self.ticker, "high"), self.data_provider.current(self.ticker, "low")

        if self.curr_high < high : self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            momentum = self.data_provider.current(self.ticker, "rocr")
            if (((self.curr_start + self.k * self.range) <= self.curr_high)
                    & (momentum > 1)):
                self.broker.order_target_weight_pv(self.ticker, np.clip((momentum-1)*5, 0, self.leverage), price=high)
        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions[self.ticker].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(self.ticker, price=self.broker.data_provider.current(self.ticker, "open"))

class VBFilterAdjusted(Stratagy):
    def __init__(self, ticker, k, leverage=1):
        super(VBFilterAdjusted, self).__init__()
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.ticker = ticker
        self.k = k
        self.leverage = leverage
        self.range = np.nan

    def set_system(self, system):
        super(VBFilterAdjusted, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        if day != self.prev_day:
            self.prev_day = day
            self.range = self.data_provider.current(self.ticker, "RANGE", timeframe=TimeFrames.Day)
            self.curr_start = self.data_provider.current(self.ticker, "open", timeframe=TimeFrames.Minute)
            self.curr_low, self.curr_high = np.inf, 0

        high, low = self.data_provider.current(self.ticker, "high", timeframe=TimeFrames.Minute), \
                    self.data_provider.current(self.ticker, "low", timeframe=TimeFrames.Minute)

        if self.curr_high < high : self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            momentum = self.data_provider.current(self.ticker, "ROCR", timeframe=TimeFrames.Day)
            ma_score = self.data_provider.current(self.ticker, "MA5", timeframe=TimeFrames.Day) \
                       / self.data_provider.current(self.ticker, "MA20", timeframe=TimeFrames.Day)
            rsi = self.data_provider.current(self.ticker, "RSI", timeframe=TimeFrames.Day)

            score = int(momentum > 1) + int(ma_score > 1) + int(rsi > 50) + 1

            if (((self.curr_start + self.k * self.range) <= self.curr_high)):
                self.broker.order_target_weight_pv(self.ticker, score/4 * self.leverage, price=high)
                #print(f"open position at {datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)}")
        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions[self.ticker].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(self.ticker, 
                                           price=self.broker.data_provider.current(self.ticker, "open", timeframe=TimeFrames.Day))
                #print(f"close position at {datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)}")


class InvTrendShortDivergence(Stratagy):
    def __init__(self, t, n, bet_once=1, loss_cut=5):
        super(InvTrendShortDivergence, self).__init__()
        """
        단기 역추세 전략
        이평선 대비 n% 급락시 매수
        이평선 대비 n% 급등시 매도
        t분 후 타임컷
        """
        self.t = t * TimeFrames.Minute
        self.n = n / 100
        self.bet_once = bet_once
        self.loss_cut = -loss_cut / 100

    def logic(self):
        for ticker in self.broker.tickers.keys():
            if ticker in self.broker.positions.keys():
                if ((self.broker.indexer.timestamp - self.broker.positions[ticker].log[-1].timestamp) >= self.t)\
                        | (self.broker.positions[ticker].unrealized_pnl_rate <= self.loss_cut):
                    self.broker.close_position(ticker)
                continue
            close = self.data_provider.current(ticker, "close")
            ma = self.data_provider.current(ticker, "MA")
            divergence = close/ma-1
            if np.abs(divergence) > self.n:
                self.broker.order_target_weight_pv(ticker=ticker, weight=-np.sign(divergence)*self.bet_once)


class VBFilterAdjustedLongShort(Stratagy):
    def __init__(self, ticker, k, leverage=1):
        super(VBFilterAdjustedLongShort, self).__init__()
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.ticker = ticker
        self.k = k
        self.leverage = leverage
        self.range = np.nan

    def set_system(self, system):
        super(VBFilterAdjustedLongShort, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        if day != self.prev_day:
            self.prev_day = day
            self.range = self.data_provider.current(self.ticker, "RANGE", timeframe=TimeFrames.Day)
            self.curr_start = self.data_provider.current(self.ticker, "open", timeframe=TimeFrames.Minute)
            self.curr_low, self.curr_high = np.inf, 0

        high, low = self.data_provider.current(self.ticker, "high", timeframe=TimeFrames.Minute), \
                    self.data_provider.current(self.ticker, "low", timeframe=TimeFrames.Minute)

        if self.curr_high < high : self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            momentum = self.data_provider.current(self.ticker, "ROCR", timeframe=TimeFrames.Day)
            ma_score = self.data_provider.current(self.ticker, "MA5", timeframe=TimeFrames.Day) \
                       / self.data_provider.current(self.ticker, "MA20", timeframe=TimeFrames.Day)
            rsi = self.data_provider.current(self.ticker, "RSI", timeframe=TimeFrames.Day)

            if (((self.curr_start + self.k * self.range) <= self.curr_high)):
                score = int(momentum > 1) + int(ma_score > 1) + int(rsi > 50) + 1
                if score > 3:
                    self.broker.order_target_weight_pv(
                        self.ticker, score/4 * self.leverage, price=high)
                #print(f"open position at {datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)}")
            elif (((self.curr_start - self.k * self.range) >= self.curr_low)):
                score = int(momentum < 1) + int(ma_score < 1) + int(rsi < 50) + 1
                if score > 3:
                    self.broker.order_target_weight_pv(
                        self.ticker, -score/4 * self.leverage, price=low)
        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions[self.ticker].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(self.ticker,
                                           price=self.broker.data_provider.current(self.ticker, "open", timeframe=TimeFrames.Day))
                #print(f"close position at {datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)}")

