from blqt.backtest.stratagies import Stratagy, TimeFrames
from blqt.backtest.stratagies import *


class RSI2Stratagy(Stratagy):
    def __init__(self, time_cut, rsi_2_threshold):
        super(RSI2Stratagy, self).__init__()
        self.time_cut = time_cut
        self.rsi_2_threshold = rsi_2_threshold

    def filter_func(self, ticker):
        rsi2 = self.data_provider.current(ticker, "RSI2", timeframe=TimeFrames.Hour)
        if rsi2 <= self.rsi_2_threshold:
            return True
        return False

    def filter_func_close(self, ticker):
        if ((self.broker.indexer.timestamp - self.broker.positions[ticker].log[-1].timestamp) >= self.time_cut)\
                or (self.data_provider.current(ticker, "RSI2", timeframe=TimeFrames.Hour) > 70):
            self.broker.close_position(ticker, price=self.data_provider.current(ticker, "close", timeframe=TimeFrames.Hour))

    def logic(self):
        [self.filter_func_close(ticker) for ticker in list(self.broker.positions.keys())]
        filtered = list(filter(self.filter_func, self.broker.tickers.keys()))
        [filtered.pop(filtered.index(x)) if x in self.broker.positions.keys() else None for x in filtered]
        bet_coeff = 1 / len(self.broker.tickers.keys())
        [self.broker.order_target_weight_margin(ticker, bet_coeff, self.data_provider.current(ticker, "close", timeframe=TimeFrames.Hour)) for ticker in filtered]


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


class AroonInvTrend(Stratagy):
    def __init__(self):
        super(AroonInvTrend, self).__init__()
