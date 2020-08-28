import gym
import blqt.backtest.brokers as brokers
import blqt.backtest.data_providers as data_providers
from blqt.backtest.historical_data import TimeIndexedData
from blqt.backtest.base import *
from talib import abstract as ta
import ray
import ray.tune as tune
import ray.rllib.agents.sac as sac

def make_data(path):
    df = pd.read_csv(path)
    df["timestamp"] = [time.mktime(datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timetuple()) for t in
                       df["timestamp"].tolist()]
    data = TimeIndexedData()
    data.from_pandas(df)

    return data

def TA_BBANDS(prices:np.ndarray, 
              timeperiod:int=5, 
              nbdevup:int=2.,
              nbdevdn:int=2.,
              matype:int=0):
    up, middle, low = ta.BBANDS(prices, 
                                timeperiod, 
                                nbdevup, 
                                nbdevdn, 
                                matype)
    ch = (up - low) / middle
    b = (prices - low) / (up - low)
    return up, middle, low, ch, b

class VBEnv(gym.Env):
    def __init__(self,
                 data_path_1day,
                 data_path_1min,
                 from_timeindex=-np.inf,
                 to_timeindex=np.inf,
                 initial_margin=10000000):

        super(VBEnv, self).__init__()

        data_1min = make_data(data_path_1min)
        data_1day = make_data(data_path_1day)

        _, _, _, ch, b = TA_BBANDS(data_1day["close"])
        data_1day.add_array("BAND_WIDTH", ch)
        data_1day.add_array("%b", b)
        data_1day.add_array("MA20", ta.SMA(data_1day["close"], timeperiod=20))
        data_1day.add_array("MA5", ta.SMA(data_1day["close"], timeperiod=5))
        data_1day.add_array("RSI", ta.RSI(data_1day["close"], timeperiod=14))
        data_1day.add_array("ROCR", ta.ROCR(data_1day["close"], timeperiod=14))
        data_1day.add_array("RANGE", data_1day["high"] - data_1day["low"])

        self.indexer = TimeIndexer(data_1min["timestamp"],
                              from_timestamp=np.clip(data_1day["timestamp"][20], from_timeindex, np.inf),
                              to_timestamp=np.clip(data_1min["timestamp"][-1], -np.inf, to_timeindex))

        self.data_provider = data_providers.BacktestDataProvider()
        self.data_provider.register_time_indexer(self.indexer)

        self.data_provider.register_ohlcv_data("Ticker", data_1min, timeframe=TimeFrames.Minute)
        self.data_provider.register_ohlcv_data("Ticker", data_1day, timeframe=TimeFrames.Day)
        
        self.broker = brokers.BackTestBroker(self.data_provider, self.indexer)
        self.broker.initialize(margin=initial_margin)
        self.initial_margin = initial_margin

        Ticker = FinancialProduct("Ticker", 0.25, 4, 0.0003, 0.1, 0.9, 0.000001)
        self.broker.add_ticker(Ticker)

        self.observation_space = gym.spaces.Box(
            np.zeros(5)-np.inf, np.zeros(5)+np.inf)
        self.action_space = gym.spaces.Box(np.array([0, 0]), np.array([2, 2]))
    
    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        if day != self.prev_day:
            self.prev_day = day
            self.range = self.data_provider.current("Ticker", "RANGE", timeframe=TimeFrames.Day)
            self.curr_start = self.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute)
            self.curr_low, self.curr_high = np.inf, 0

        high, low = self.data_provider.current("Ticker", "high", timeframe=TimeFrames.Minute), \
                    self.data_provider.current("Ticker", "low", timeframe=TimeFrames.Minute)

        if self.curr_high < high : self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            k_range = self.k * self.range
            high_breakout = self.curr_start + k_range
            low_breakout = self.curr_start - k_range
            if (high_breakout <= self.curr_high):
                self.broker.order_target_weight_pv("Ticker", self.bet, high_breakout)
            elif (high_breakout >= self.curr_low):
                self.broker.order_target_weight_pv("Ticker", -self.bet, low_breakout)

        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions["Ticker"].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(
                    "Ticker",price=self.broker.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute))
                if self.temp == len(self.broker.trade_hist_rate):
                    ret = 0
                else:
                    ret = self.broker.trade_hist_rate[-1]
                self.temp = len(self.broker.trade_hist_rate)
                return ret

    def run_logic(self):
        ret = None
        while ret is None:
            self.broker.indexer.move()
            self.broker.calc_pv()
            self.broker.update_weight()
            ret = self.logic()
            done = True if (self.indexer.lastidx - 2) == (self.indexer.idx) else False
            if done:
                return None
        return ret

    @staticmethod
    def convert_reward(ret):
        if ret > 0:
            return ret
        elif ret < 0:
            return -np.exp(-ret)
        return 0

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

    def reset(self):
        self.indexer.idx = -1
        self.indexer.move()
        self.broker.initialize(self.initial_margin)

        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.range = np.nan

        self.temp = 0
        self.broker.trade_hist = []
        self.broker.trade_hist_rate = []

        while True:
            self.indexer.move()
            observation = self._get_observation()
            if not (observation == np.nan).any():
                self.prev_day = datetime.datetime.fromtimestamp(self.indexer.timestamp).day
                return observation
        
    def step(self, action:np.ndarray):
        self.k = action[0]
        self.bet = action[1]

        ret = self.run_logic()
        if ret is None:
            reward = 0
        else:
            reward = self.convert_reward(ret)
        next_observation = self._get_observation()
        done = True if (self.indexer.lastidx-2) == (self.indexer.idx) else False
        return reward, next_observation, done, {}


if __name__ == '__main__':
    config = sac.DEFAULT_CONFIG.copy()
    config["num_workers"] = 4
    config["num_gpus"] = 1
    config["env"] = VBEnv
    config["env_config"] = {
        "data_path_1day":
            "../../data/ETHUSD_20180802-20200824_1day.csv",
        "data_path_1min":
            "../../data/ETHUSD_20180802-20200824_1hour.csv",
    }
    env = VBEnv("../../data/ETHUSD_20180802-20200824_1day.csv", "../../data/ETHUSD_20180802-20200824_1hour.csv")
    tune.run(
        sac.SACTrainer,
        config=config,
        local_dir="/content/gdrive/My Drive/VB_Agent/",
        checkpoint_at_end=True,
        checkpoint_freq=1000,
    )

        
        









