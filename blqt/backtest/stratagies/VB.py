from blqt.backtest.stratagies import Stratagy, TimeFrames
from blqt.backtest.stratagies.VBRL import VBAgentStratagyMT
import datetime
import numpy as np

class VBFilterAdjustedLongShortMT(VBAgentStratagyMT):
    def __init__(self, k=0.6, leverage=1, universe=None):
        super(VBFilterAdjustedLongShortMT, self).__init__(None, k, leverage, universe)

    def update_params(self):
        for ticker in self.universe:
            rng = self.data_provider.current(ticker, "RANGE", timeframe=TimeFrames.Day)
            curr_start = self.data_provider.current(ticker, "open", timeframe=TimeFrames.Minute)
            curr_low, curr_high = np.inf, 0

            self.info_dict[ticker]["rng"] = rng
            self.info_dict[ticker]["curr_start"] = curr_start
            self.info_dict[ticker]["curr_low"] = curr_low
            self.info_dict[ticker]["curr_high"] = curr_high

            momentum = self.data_provider.current(ticker, "ROCR", timeframe=TimeFrames.Day)
            ma_score = self.data_provider.current(ticker, "MA5", timeframe=TimeFrames.Day) \
                       / self.data_provider.current(ticker, "MA20", timeframe=TimeFrames.Day)
            rsi = self.data_provider.current(ticker, "RSI", timeframe=TimeFrames.Day)

            positive = int(momentum > 1) + int(ma_score > 1) + int(rsi > 50)
            negative = int(momentum < 1) + int(ma_score < 1) + int(rsi < 50)

            if positive > 2:
                filtering = 1
            elif negative > 2:
                filtering = -1
            else:
                filtering = 0

            bet = 1 * self.leverage

            self.info_dict[ticker]["filtering"] = filtering
            self.info_dict[ticker]["bet"] = bet


class VBSingleCoin(Stratagy):
    def __init__(self, ticker, k, leverage=1):
        super(VBSingleCoin, self).__init__()
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.ticker = ticker
        self.k = k
        self.leverage = leverage
        self.rng = np.nan

    def set_system(self, system):
        super(VBSingleCoin, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day
        if day != self.prev_day:
            self.prev_day = day
            self.rng = self.curr_high - self.curr_low
            self.curr_start = self.data_provider.current(self.ticker, "open")
            self.curr_low, self.curr_high = np.inf, 0

        high, low = self.data_provider.current(self.ticker, "high"), self.data_provider.current(self.ticker, "low")

        if self.curr_high < high : self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            if (self.curr_start + self.k * self.rng) <= self.curr_high:
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
        self.rng = np.nan

    def set_system(self, system):
        super(VBSingleCoinActualMomentumFiltered, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day
        if day != self.prev_day:
            self.prev_day = day
            self.rng = self.curr_high - self.curr_low
            self.curr_start = self.data_provider.current(self.ticker, "open")
            self.curr_low, self.curr_high = np.inf, 0

        high, low = self.data_provider.current(self.ticker, "high"), self.data_provider.current(self.ticker, "low")

        if self.curr_high < high : self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            momentum = self.data_provider.current(self.ticker, "rocr")
            if (((self.curr_start + self.k * self.rng) <= self.curr_high)
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
        self.rng = np.nan

    def set_system(self, system):
        super(VBFilterAdjusted, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        if day != self.prev_day:
            self.prev_day = day
            self.rng = self.data_provider.current(self.ticker, "rng", timeframe=TimeFrames.Day)
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

            if (((self.curr_start + self.k * self.rng) <= self.curr_high)):
                self.broker.order_target_weight_pv(self.ticker, score/4 * self.leverage)
                ##(f"open position at {datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)}")
        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions[self.ticker].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(self.ticker)
                ##(f"close position at {datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)}")


class VBFilterAdjustedLongShort(Stratagy):
    def __init__(self, ticker, k, leverage=1):
        super(VBFilterAdjustedLongShort, self).__init__()
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.ticker = ticker
        self.k = k
        self.leverage = leverage
        self.rng = np.nan

    def set_system(self, system):
        super(VBFilterAdjustedLongShort, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        if day != self.prev_day:
            self.prev_day = day
            self.rng = self.data_provider.current(self.ticker, "rng", timeframe=TimeFrames.Day)
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

            if (((self.curr_start + self.k * self.rng) <= self.curr_high)):
                score = int(momentum > 1) + int(ma_score > 1) + int(rsi > 50) + 1
                if score > 3:
                    self.broker.order_target_weight_pv(
                        self.ticker, score/4 * self.leverage)
                ##(f"open position at {datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)}")
            elif (((self.curr_start - self.k * self.rng) >= self.curr_low)):
                score = int(momentum < 1) + int(ma_score < 1) + int(rsi < 50) + 1
                if score > 3:
                    self.broker.order_target_weight_pv(
                        self.ticker, -score/4 * self.leverage)
        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions[self.ticker].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(self.ticker)
                ##(f"close position at {datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)}")
