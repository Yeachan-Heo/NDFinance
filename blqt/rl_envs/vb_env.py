import gym
import blqt.backtest.brokers as brokers
import blqt.backtest.data_providers as data_providers
from blqt.backtest.historical_data import TimeIndexedData
from blqt.backtest.base import *
from talib import abstract as ta
import ray
import ray.tune as tune
import ray.rllib.agents.sac as sac
import ray.rllib.agents.ppo as ppo
import ray.rllib.agents.ddpg as ddpg


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
    def __init__(self, env_config):

        data_path_1min = env_config["data_path_1min"]
        data_path_1day = env_config["data_path_1day"]
        from_timeindex = env_config["from_timeindex"]
        to_timeindex = env_config["to_timeindex"]

        initial_margin = 10000000

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
                              to_timestamp=np.clip(data_1day["timestamp"][-2], -np.inf, to_timeindex))

        self.data_provider = data_providers.BacktestDataProvider()
        self.data_provider.register_time_indexer(self.indexer)

        self.data_provider.register_ohlcv_data("Ticker", data_1min, timeframe=TimeFrames.Minute)
        self.data_provider.register_ohlcv_data("Ticker", data_1day, timeframe=TimeFrames.Day)
        
        self.broker = brokers.BackTestBroker(self.data_provider, self.indexer)
        self.broker.initialize(margin=initial_margin)
        self.initial_margin = initial_margin

        Ticker = FinancialProduct("Ticker", 1, 1, 0.0003, 1, 1, 0.000001)
        self.broker.add_ticker(Ticker)

        self.observation_space = gym.spaces.Box(
            np.zeros(5)-np.inf, np.zeros(5)+np.inf)
        self.action_space = gym.spaces.Box(np.array([0, 0]), np.array([1.2, 1]))
    
    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        day_changed = False
        if day != self.prev_day:
            self.prev_day = day
            self.range = self.data_provider.current("Ticker", "RANGE", timeframe=TimeFrames.Day)
            self.curr_start = self.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute)
            self.curr_low, self.curr_high = np.inf, 0
            day_changed = True


        high, low = self.data_provider.current("Ticker", "high", timeframe=TimeFrames.Minute), \
                    self.data_provider.current("Ticker", "low", timeframe=TimeFrames.Minute)

        if self.curr_high < high : self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            if day_changed:
                return -0.03
            k_range = self.k * self.range
            high_breakout = self.curr_start + k_range
            low_breakout = self.curr_start - k_range
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
        return ret

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
        self.ks = []
        self.bets = []

        while True:
            self.indexer.move()
            observation = self._get_observation()
            if not (observation == np.nan).any():
                self.prev_day = datetime.datetime.fromtimestamp(self.indexer.timestamp).day
                return observation
        
    def step(self, action:np.ndarray):
        self.k = action[0]
        self.ks.append(self.k)
        self.bet = action[1]
        self.bets.append(self.bet)
        ret = self.run_logic()
        if ret is None:
            reward = 0
        else:
            reward = self.convert_reward(ret)
        next_observation = self._get_observation()
        done = True if (self.indexer.lastidx-2) == (self.indexer.idx) else False
        if done:
            print(f"overall P&L : {np.round(self.broker.pv/self.initial_margin*100-100, 2)}%, "
                  f"k:{np.round(np.mean(self.k), 2)}, bet:{np.round(np.mean(self.bet), 2)}")
        return next_observation, reward, done, {}



class VBEnv_V2(VBEnv):
    def __init__(self, *args, **kwargs):
        super(VBEnv_V2, self).__init__(*args, **kwargs)
        self.action_space = gym.spaces.Box(np.array([0.5, 0]), np.array([1.2, 1]))

from blqt.backtest import utils

class VBEnv_V3(gym.Env):
    def __init__(self, env_config):

        data_path_1min = env_config["data_path_1min"]
        data_path_1day = env_config["data_path_1day"]
        from_timeindex = env_config["from_timeindex"]
        to_timeindex = env_config["to_timeindex"]
        self.k = env_config["k"]

        if isinstance(to_timeindex, str):
            to_timeindex = time.mktime(datetime.datetime.strptime(to_timeindex, "%Y-%m-%d").timetuple())

        initial_margin = 10000000

        super(VBEnv_V3, self).__init__()

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
                                   to_timestamp=np.clip(data_1day["timestamp"][-2], -np.inf, to_timeindex))

        self.data_provider = data_providers.BacktestDataProvider()
        self.data_provider.register_time_indexer(self.indexer)

        self.data_provider.register_ohlcv_data("Ticker", data_1min, timeframe=TimeFrames.Minute)
        self.data_provider.register_ohlcv_data("Ticker", data_1day, timeframe=TimeFrames.Day)

        self.broker = brokers.BackTestBroker(self.data_provider, self.indexer)
        self.broker.initialize(margin=initial_margin)
        self.initial_margin = initial_margin

        Ticker = FinancialProduct("Ticker", 1, 1, 0.0004, 1, 1, 0.000001)
        self.broker.add_ticker(Ticker)

        self.observation_space = gym.spaces.Box(
            np.zeros(5) - np.inf, np.zeros(5) + np.inf)
        self.action_space = gym.spaces.Box(np.array([-1, 0]), np.array([1, 1]))
        self.default_reward = -0.03

    def logic(self):
        dt = datetime.datetime.fromtimestamp(self.broker.indexer.timestamp)
        day = dt.day

        day_changed = False
        if day != self.prev_day:
            self.prev_day = day
            self.range = self.data_provider.current("Ticker", "RANGE", timeframe=TimeFrames.Day)
            self.curr_start = self.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute)
            self.curr_low, self.curr_high = np.inf, 0
            day_changed = True

        high, low = self.data_provider.current("Ticker", "high", timeframe=TimeFrames.Minute), \
                    self.data_provider.current("Ticker", "low", timeframe=TimeFrames.Minute)

        if self.curr_high < high: self.curr_high = high
        if self.curr_low > low: self.curr_low = low

        if not self.broker.positions:
            if day_changed:
                return 0
            k_range = self.k * self.range
            high_breakout = self.curr_start + k_range
            low_breakout = self.curr_start - k_range
            if (high_breakout <= self.curr_high) & (self.filtering == 1):
                self.broker.order_target_weight_pv("Ticker", self.bet)
            elif (low_breakout >= self.curr_low) & (self.filtering == -1):
                self.broker.order_target_weight_pv("Ticker", -self.bet)

        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions["Ticker"].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(
                    "Ticker", price=self.broker.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute))
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

    def convert_reward(self, ret):
        return ret if ret > 0 else ret + self.default_reward

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
        self.ks = []
        self.bets = []

        while True:
            self.indexer.move()
            observation = self._get_observation()
            if not (observation == np.nan).any():
                self.prev_day = datetime.datetime.fromtimestamp(self.indexer.timestamp).day
                return observation

    def step(self, action: np.ndarray):
        self.filtering = np.round(action[0]).astype(int)
        self.bet = action[1]

        ret = self.run_logic()
        if ret is None:
            reward = 0
        else:
            reward = self.convert_reward(ret)

        next_observation = self._get_observation()
        done = True if (self.indexer.lastidx - 2) == (self.indexer.idx) else False
        if done:
            print(f"overall P&L : {np.round(self.broker.pv / self.initial_margin * 100 - 100, 2)}%")
        return next_observation, reward, done, {}





