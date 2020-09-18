from blqt.backtest.base import *

class VBAgentStratagy(Stratagy):
    def __init__(self, agent):
        super(VBAgentStratagy, self).__init__()
        self.agent = agent
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.rng = np.nan

    def set_system(self, system):
        super(VBAgentStratagy, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day
        self.update_params()

    def update_params(self):
        self.k, self.bet = \
            self.agent.get_policy().compute_single_action(self._get_observation())[-1]["action_dist_inputs"][:2]
        self.k = np.clip(self.k, 0, 1.2)
        self.bet = np.clip(self.bet, 0, 1)
        #(self.k, self.bet)

    def _get_observation(self):
        ma20 = self.data_provider.current("Ticker", "MA20", timeframe=TimeFrames.Day)
        ma5 = self.data_provider.current("Ticker", "MA5", timeframe=TimeFrames.Day)
        rsi = self.data_provider.current("Ticker", "RSI", timeframe=TimeFrames.Day)
        rocr = self.data_provider.current("Ticker", "ROCR", timeframe=TimeFrames.Day)
        bw = self.data_provider.current("Ticker", "BAND_WIDTH", timeframe=TimeFrames.Day)
        b = self.data_provider.current("Ticker", "%b", timeframe=TimeFrames.Day)
        ma_div = ma5 / ma20
        rsi /= 100
        return np.array([ma_div, rsi, rocr, bw, b])

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        if day != self.prev_day:
            self.prev_day = day
            self.rng = self.data_provider.current("Ticker", "rng", timeframe=TimeFrames.Day)
            self.curr_start = self.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute)
            self.curr_low, self.curr_high = np.inf, 0
            self.update_params()

        high, low = self.data_provider.current("Ticker", "high", timeframe=TimeFrames.Minute), \
                    self.data_provider.current("Ticker", "low", timeframe=TimeFrames.Minute)

        if self.curr_high < high : self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            k_rng = self.k * self.rng
            high_breakout = self.curr_start + k_rng
            low_breakout = self.curr_start - k_rng

            if (high_breakout <= self.curr_high):
                self.broker.order_target_weight_pv("Ticker", self.bet)
            elif (low_breakout >= self.curr_low):
                self.broker.order_target_weight_pv("Ticker", -self.bet)

        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions["Ticker"].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(
                    "Ticker",price=self.broker.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute))


class VBAgentStratagyV2(VBAgentStratagy):
    def __init__(self, *args, **kwargs):
        super(VBAgentStratagyV2, self).__init__(*args, **kwargs)



    def update_params(self):
        self.k, self.bet = \
            self.agent.get_policy().compute_single_action(self._get_observation())[-1]["action_dist_inputs"][:2]
        self.k = np.clip(self.k, 0.5, 1.2)
        self.bet = np.clip(self.bet, 0, 1)


class VBAgentStratagyV3(Stratagy):
    def __init__(self, agent, k=0.6):
        self.k = k
        self.agent = agent
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.rng = np.nan
        super(VBAgentStratagyV3, self).__init__()

    def set_system(self, system):
        super(VBAgentStratagyV3, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day
        self.update_params()

    def _get_observation(self):
        ma20 = self.data_provider.current("Ticker", "MA20", timeframe=TimeFrames.Day)
        ma5 = self.data_provider.current("Ticker", "MA5", timeframe=TimeFrames.Day)
        rsi = self.data_provider.current("Ticker", "RSI", timeframe=TimeFrames.Day)
        rocr = self.data_provider.current("Ticker", "ROCR", timeframe=TimeFrames.Day)
        bw = self.data_provider.current("Ticker", "BAND_WIDTH", timeframe=TimeFrames.Day)
        b = self.data_provider.current("Ticker", "%b", timeframe=TimeFrames.Day)
        ma_div = ma5 / ma20
        rsi /= 100
        return np.array([ma_div, rsi, rocr, bw, b])

    def update_params(self):
        self.filtering, self.bet = \
            self.agent.get_policy().compute_single_action(self._get_observation())[-1]["action_dist_inputs"][:2]
        self.filtering = np.round(np.clip(self.filtering, -1, 1)).astype(int)
        self.bet = np.clip(self.bet, 0, 1)

    def logic(self):

        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        if day != self.prev_day:
            self.prev_day = day
            self.rng = self.data_provider.current("Ticker", "RANGE", timeframe=TimeFrames.Day)
            self.curr_start = self.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute)
            self.curr_low, self.curr_high = np.inf, 0
            self.update_params()

        high, low = self.data_provider.current("Ticker", "high", timeframe=TimeFrames.Minute), \
                    self.data_provider.current("Ticker", "low", timeframe=TimeFrames.Minute)

        if self.curr_high < high: self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if (not self.broker.positions) & (self.bet > 0):
            k_rng = self.k * self.rng
            high_breakout = self.curr_start + k_rng
            low_breakout = self.curr_start - k_rng
            if (high_breakout <= self.curr_high) & (self.filtering == 1):
                self.broker.order_target_weight_pv("Ticker", self.bet)
                #print("long", self.broker.indexer.datetime, self.bet)
            elif (low_breakout >= self.curr_low) & (self.filtering == -1):
                self.broker.order_target_weight_pv("Ticker", -self.bet)
                #print("short", self.broker.indexer.datetime, self.bet)


        elif self.broker.positions:
            #print(self.broker.positions)
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions["Ticker"].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(
                    "Ticker", price=self.broker.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute))
                #print("close", self.broker.indexer.datetime)


class VBAgentStratagyMT(Stratagy):
    def __init__(self, agent, k=0.6, min_bet=0, max_leverage=1, leverage_coeff=1, time_cut=9, universe=None):
        self.universe = universe
        self.k = k
        self.agent = agent
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.rng = np.nan
        self.leverage = leverage_coeff
        self.min_bet = min_bet
        self.max_leverage = max_leverage
        self.time_cut = time_cut
        super(VBAgentStratagyMT, self).__init__()

    def set_system(self, system):
        super(VBAgentStratagyMT, self).set_system(system)
        self.prev_day = \
            datetime.datetime.fromtimestamp(self.broker.indexer.timestamp).day
        if self.universe is None:
            self.universe = self.broker.tickers.keys()
        self.info_dict = {key: {} for key in self.universe}
        self.update_params()


    def _get_observation(self, ticker):
        ma20 = self.data_provider.current(ticker, "MA20", timeframe=TimeFrames.Day)
        ma5 = self.data_provider.current(ticker, "MA5", timeframe=TimeFrames.Day)
        rsi = self.data_provider.current(ticker, "RSI", timeframe=TimeFrames.Day)
        rocr = self.data_provider.current(ticker, "ROCR", timeframe=TimeFrames.Day)
        bw = self.data_provider.current(ticker, "BAND_WIDTH", timeframe=TimeFrames.Day)
        b = self.data_provider.current(ticker, "%b", timeframe=TimeFrames.Day)
        ma_div = ma5 / ma20
        rsi /= 100
        return np.array([ma_div, rsi, rocr, bw, b])

    def update_params(self):
        for ticker in self.universe:
            rng = self.data_provider.current(ticker, "RANGE", timeframe=TimeFrames.Day)
            curr_start = self.data_provider.current(ticker, "open", timeframe=TimeFrames.Minute)
            curr_low, curr_high = np.inf, 0

            self.info_dict[ticker]["rng"] = rng
            self.info_dict[ticker]["curr_start"] = curr_start
            self.info_dict[ticker]["curr_low"] = curr_low
            self.info_dict[ticker]["curr_high"] = curr_high

            filtering, bet = \
                self.agent.get_policy().compute_single_action(self._get_observation(ticker))[-1]["action_dist_inputs"][:2]

            filtering = np.round(np.clip(filtering, -1, 1)).astype(int)

            bet = np.clip(bet, self.min_bet, self.max_leverage) * self.leverage

            self.info_dict[ticker]["filtering"] = filtering
            self.info_dict[ticker]["bet"] = bet


    def logic(self):

        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        if day != self.prev_day:
            self.prev_day = day
            self.update_params()


        for ticker in self.universe:
            bet, filtering = self.info_dict[ticker]["bet"], self.info_dict[ticker]["filtering"]
            bet *= (len(self.universe) - len(self.broker.positions.keys())) / len(self.universe)
            rng, curr_start = self.info_dict[ticker]["rng"], self.info_dict[ticker]["curr_start"]

            high, low = self.data_provider.current(ticker, "high", timeframe=TimeFrames.Minute), \
                        self.data_provider.current(ticker, "low", timeframe=TimeFrames.Minute)

            if self.info_dict[ticker]["curr_high"] < high: self.info_dict[ticker]["curr_high"] = high
            if self.info_dict[ticker]["curr_high"] > low: self.info_dict[ticker]["curr_low"] = low

            if (not ticker in self.broker.positions.keys()):
                k_rng = rng * self.k
                high_breakout = curr_start + k_rng
                low_breakout = curr_start - k_rng
                if (high_breakout <= self.info_dict[ticker]["curr_high"]) & (filtering == 1):
                    self.broker.order_target_weight_margin(ticker, bet)
                    #print("long", self.broker.indexer.datetime, self.bet)
                elif (low_breakout >= self.info_dict[ticker]["curr_low"]) & (filtering == -1):
                    self.broker.order_target_weight_margin(ticker, -bet)
                    #print("short", self.broker.indexer.datetime, self.bet)


            elif ticker in self.broker.positions.keys():
                #print(self.broker.positions)
                dt_pos = datetime.datetime.fromtimestamp(self.broker.positions[ticker].log[-1].timestamp)
                day_pos = dt_pos.day
                hr = dt.hour
                if (day_pos != day) & (hr >= self.time_cut):
                    self.broker.close_position(
                        ticker, price=self.broker.data_provider.current(ticker, "open", timeframe=TimeFrames.Minute))
                #print("close", self.broker.indexer.datetime)
