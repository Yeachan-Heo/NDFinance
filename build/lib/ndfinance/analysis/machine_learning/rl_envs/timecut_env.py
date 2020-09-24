from blqt.data_utils import *
import gym


class TimeCutEnv(gym.Env):
    def __init__(self, env_config):
        super(TimeCutEnv, self).__init__()
        
        data_path = env_config["data_path"]
        self.data = make_bitmex_data(data_path)
        self.timecut = TimeFrames.Hour
        
        initial_margin = 10000000

        _, _, _, ch, b = technical.TA_BBANDS(self.data["close"])
        self.data.add_array("BAND_WIDTH", ch)
        self.data.add_array("%b", b)
        self.data.add_array("MA20", technical.SMA(self.data["close"], timeperiod=20))
        self.data.add_array("MA5", technical.SMA(self.data["close"], timeperiod=5))
        self.data.add_array("RSI", technical.RSI(self.data["close"], timeperiod=14))
        self.data.add_array("ROCR", technical.ROCR(self.data["close"], timeperiod=14))
        self.data.add_array("AROONOSC", technical.AROONOSC(self.data["high"], self.data["low"], timeperiod=14))

        self.indexer = base.TimeIndexer(
            self.data["timestamp"], from_timestamp=self.data["timestamp"][20])

        self.data_provider = data_providers.BacktestDataProvider()
        self.data_provider.register_time_indexer(self.indexer)

        self.data_provider.register_ohlcv_data("Ticker", self.data)

        self.broker = brokers.BackTestBroker(self.data_provider, self.indexer)
        self.broker.initialize(margin=initial_margin)
        self.initial_margin = initial_margin

        Ticker = FinancialProduct("Ticker", 1, 1, 0.0001, 1, 1, 0.000001)
        self.broker.add_ticker(Ticker)

        self.observation_space = gym.spaces.Box(
            np.zeros(6) - np.inf, np.zeros(6) + np.inf)
        self.action_space = gym.spaces.Box(np.array([-1, 0]), np.array([1, 1]))

        self.default_reward = -0.01

    def _get_observation(self):
        ma20 = self.data_provider.current("Ticker", "MA20")
        ma5 = self.data_provider.current("Ticker", "MA5")
        rsi = self.data_provider.current("Ticker", "RSI")
        rocr = self.data_provider.current("Ticker", "ROCR")
        bw = self.data_provider.current("Ticker", "BAND_WIDTH")
        b = self.data_provider.current("Ticker", "%b")
        aroonosc = self.data_provider.current("Ticker", "AROONOSC") / 100
        ma_div = ma5 / ma20
        rsi /= 100

        return np.array([ma_div, rsi, rocr, bw, b, aroonosc])

    def reset(self):
        self.indexer.idx = -1
        self.indexer.move()
        self.broker.initialize(self.initial_margin)

        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.range = np.nan

        self.temp = 0
        self.broker.trade_hist = []
        self.broker.trade_hist_percentage = []
        self.ks = []
        self.bets = []
        self.prev_len = 0

        while True:
            self.indexer.move()
            observation = self._get_observation()
            if not (observation == np.nan).any():
                self.prev_day = datetime.datetime.fromtimestamp(self.indexer.timestamp).day
                return observation

    def is_done(self):
        return True if (self.indexer.lastidx - 3) == (self.indexer.idx) else False

    def logic(self):
        if (self.side == 0) or (self.weight == 0):
            return 0

        if self.broker.positions:
            if (self.broker.indexer.timestamp - self.broker.positions["Ticker"].log[-1].timestamp) >= self.timecut:
                return self.broker.close_position("Ticker")
        else:
            return self.broker.order_target_weight_pv("Ticker", weight=self.weight * self.side)


    def step(self, action):
        self.side, self.weight = action
        self.side = np.round(self.side)
        
        self.broker.indexer.move()
        self.broker.calc_pv()
        self.broker.update_weight()
        reward = self.logic()

        if reward <= 0:
            reward += self.default_reward

        return self._get_observation(), reward, self.is_done(), {}

if __name__ == '__main__':
    env_cfg = {
        "data_path" : "/tmp/pycharm_project_22/data/bitmex/XBTUSD_1H.csv"
    }
    env = TimeCutEnv(env_cfg)
    env.reset()
    while True:
        r, o, done, _,  = env.step([1, 1])
        print(r, o)
        if done:
            break
