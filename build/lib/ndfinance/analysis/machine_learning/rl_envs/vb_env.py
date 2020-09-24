import gym
import ndfinance.brokers.backtest.brokers as brokers
import ndfinance.brokers.backtest.data_providers as data_providers
from ndfinance.brokers.backtest import TimeIndexedData
from blqt.old.backtest.base import *
from talib import abstract as ta


def make_data(path, coeff=1):
    df = pd.read_csv(path)
    df["close"] *= coeff
    df["open"] *= coeff
    df["high"] *= coeff
    df["low"] *= coeff
    df["volume"] /= coeff
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
                if self.temp == len(self.broker.trade_hist_percentage):
                    ret = 0
                else:
                    ret = self.broker.trade_hist_percentage[-1]
                self.temp = len(self.broker.trade_hist_percentage)
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
        self.broker.trade_hist_percentage = []
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

        Ticker = FinancialProduct("Ticker", 1e-8, 1e-8, 0.0004, 1, 1, 1e-6)
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
                self.broker.order_target_weight_margin("Ticker", self.bet)
            elif (low_breakout >= self.curr_low) & (self.filtering == -1):
                self.broker.order_target_weight_margin("Ticker", -self.bet)

        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions["Ticker"].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= 9):
                self.broker.close_position(
                    "Ticker", price=self.broker.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute))
                if self.temp == len(self.broker.trade_hist_percentage):
                    ret = 0
                else:
                    ret = self.broker.trade_hist_percentage[-1]
                self.temp = len(self.broker.trade_hist_percentage)
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
        self.broker.trade_hist_percentage = []
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



class VBEnv_V4(VBEnv_V3):
    def __init__(self, *args, **kwargs):
        super(VBEnv_V4, self).__init__(*args, **kwargs)
        self.action_space = gym.spaces.Box(np.array([-1, 0.01]), np.array([1, 1]))

class VBEnv_V5(VBEnv_V3):
    def __init__(self, *args, **kwargs):
        super(VBEnv_V5, self).__init__(*args, **kwargs)
        self.action_space = gym.spaces.Box(np.array([-1, 0]), np.array([1, 3]))
        self.default_reward = -0.1

class VBEnv_V6(VBEnv_V5):
    def __init__(self, *args, **kwargs):
        super(VBEnv_V6, self).__init__(*args, **kwargs)

    def convert_reward(self, ret):
        if ret > 0:
            return ret
        else:
            return ret*5 + self.default_reward


class VBEnv_V7(VBEnv_V5):
    def __init__(self, *args, **kwargs):
        super(VBEnv_V7, self).__init__(*args, **kwargs)
        self.default_reward = -0.005

    def convert_reward(self, ret):
        if ret > 0:
            return ret
        else:
            return ret*0.5 + self.default_reward


class VBEnv_V8(VBEnv_V3):
    def __init__(self, *args, **kwargs):
        super(VBEnv_V8, self).__init__(*args, **kwargs)
        self.action_space = gym.spaces.Box(np.array([-1, 0.1]), np.array([1, 3]))
        self.default_reward = self.default_reward * 3


class VBRLEnv(gym.Env):
    def __init__(self, env_config):
        super(VBRLEnv, self).__init__()

        self.data_path_1min = env_config["data_path_1min"]
        self.data_path_1day = env_config["data_path_1day"]
        self.from_timeindex = env_config["from_timeindex"]
        self.to_timeindex = env_config["to_timeindex"]
        self.k = env_config["k"]
        self.time_cut = env_config["time_cut"]
        self.epi_len = env_config["episode_len"]
        self.default_reward = env_config["default_reward"]
        self.max_leverage = env_config["max_leverage"]
        self.min_bet = env_config["min_bet"]
        self.window_size = int(self.epi_len / TimeFrames.Day)

        self.observation_space = gym.spaces.Box(
            np.zeros(5) - 100, np.zeros(5) + 100)
        self.action_space = gym.spaces.Box(np.array([-1, self.min_bet]), np.array([1, self.max_leverage]))
        self.initial_margin = 10000
        self.broker = None
        self.initialize_system()


    def initialize_system(self):
        i = np.random.randint(0, len(self.data_path_1min))
        data_path_1min = self.data_path_1min[i]
        data_path_1day = self.data_path_1day[i]

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

        n = np.random.randint(low=0, high=len(data_1day["timestamp"])-21-self.window_size)

        self.indexer = TimeIndexer(data_1min["timestamp"],
                                   from_timestamp=np.clip(data_1day["timestamp"][21+n], self.from_timeindex, np.inf),
                                   to_timestamp=np.clip(data_1day["timestamp"][21+n+self.window_size], -np.inf, self.to_timeindex))

        self.data_provider = data_providers.BacktestDataProvider()
        self.data_provider.register_time_indexer(self.indexer)

        self.data_provider.register_ohlcv_data("Ticker", data_1min, timeframe=TimeFrames.Minute)
        self.data_provider.register_ohlcv_data("Ticker", data_1day, timeframe=TimeFrames.Day)

        self.broker = brokers.BackTestBroker(self.data_provider, self.indexer)
        self.broker.initialize(margin=self.initial_margin)

        Ticker = FinancialProduct("Ticker", 1e-8, 1e-8, 0.0004, 1/self.max_leverage, 1e-6)
        self.broker.add_ticker(Ticker)


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
                self.broker.order_target_weight_margin("Ticker", self.bet)
            elif (low_breakout >= self.curr_low) & (self.filtering == -1):
                self.broker.order_target_weight_margin("Ticker", -self.bet)

        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions["Ticker"].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= self.time_cut):
                self.broker.close_position(
                    "Ticker", price=self.broker.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute))
                if self.temp == len(self.broker.trade_hist_percentage_weighted):
                    ret = 0
                else:
                    ret = self.broker.trade_hist_percentage_weighted[-1]
                self.temp = len(self.broker.trade_hist_percentage_weighted)
                return ret

    def run_logic(self):
        ret = None
        while ret is None:
            self.broker.indexer.move()
            self.broker.calc_pv()
            self.broker.update_weight()
            ret = self.logic()
            end = True if (self.indexer.lastidx - 2) == (self.indexer.idx) else False
            if end:
                return 0
        return ret

    def is_end(self):
        end = True if (self.indexer.lastidx - 2) == (self.indexer.idx) else False
        return end

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
        self.initialize_system()
        self.curr_low, self.curr_high = np.inf, 0
        self.curr_start = 0
        self.range = np.nan

        self.temp = 0
        self.broker.trade_hist = []
        self.broker.trade_hist_percentage = []
        self.ks = []
        self.bets = []

        self.prev_day = self.indexer.datetime.day
        self.prev_epi_ts = self.indexer.timestamp
        self.pv_lst = []

        while True:
            self.indexer.move()
            observation = self._get_observation()
            if not (observation == np.nan).any():
                self.prev_day = self.indexer.datetime.day
                self.prev_epi_ts = self.indexer.timestamp
                if self.is_end():
                    self.initialize_system()
                    return self.reset()
                return observation

    def step(self, action: np.ndarray):
        self.filtering = np.round(action[0]).astype(int)
        self.bet = action[1]

        ret = self.run_logic()
        reward = self.convert_reward(ret)
        next_observation = self._get_observation()

        if (next_observation == np.nan).any():
            return self.observation_space.sample(), reward, True, {}

        end = self.is_end()
        self.broker.calc_pv()
        self.pv_lst.append(self.broker.pv)

        return next_observation, reward, end, {}

from ray.rllib.agents.callbacks import DefaultCallbacks
from ray.rllib.utils.annotations import PublicAPI

@PublicAPI
class VBRLEnv_Callback(DefaultCallbacks):
    def __init__(self, *args, **kwargs):
        super(VBRLEnv_Callback, self).__init__(*args, **kwargs)

    @PublicAPI
    def on_episode_end(self, worker, base_env,
                       policies,
                       episode, **kwargs):
        env = base_env.get_unwrapped()[-1]

        episode.custom_metrics["average_profit_and_loss"] = np.mean(env.broker.trade_hist_percentage_weighted)*100
        episode.custom_metrics["cagr"] = calc_cagr_v2(env.pv_lst, n_days=env.window_size)

        try: episode.custom_metrics["mdd"] = np.abs(get_mdd(env.pv_lst)[-1]*100)
        except: episode.custom_metrics["mdd"] = 1
        episode.custom_metrics["cagr_mdd_percentage"] = episode.custom_metrics["cagr"] / episode.custom_metrics["mdd"]

        win_lst = list(filter(lambda x: x > 0, env.broker.trade_hist))
        lose_lst = list(filter(lambda x: x < 0, env.broker.trade_hist))

        episode.custom_metrics["profit_loss_percentage"] = np.abs(np.mean(win_lst)/np.mean(lose_lst))
        episode.custom_metrics["win_percentage"] = len(win_lst) / len(env.broker.trade_hist) * 100 if env.broker.trade_hist else 0
        episode.custom_metrics["trade_freq"] = len(env.broker.trade_hist) / env.window_size  * 100


class VBRLEnv_V2(VBRLEnv):
    def __init__(self, env_config):
        super(VBRLEnv_V2, self).__init__(env_config)

    def reset(self):
        self.temp_ret = 0
        return super(VBRLEnv_V2, self).reset()


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
                temp = self.temp_ret
                self.temp_ret = 0
                return temp
            k_range = self.k * self.range
            high_breakout = self.curr_start + k_range
            low_breakout = self.curr_start - k_range
            if (high_breakout <= self.curr_high) & (self.filtering == 1):
                self.broker.order_target_weight_margin("Ticker", self.bet)
            elif (low_breakout >= self.curr_low) & (self.filtering == -1):
                self.broker.order_target_weight_margin("Ticker", -self.bet)
            else:
                if ((high_breakout <= self.curr_high) or (low_breakout >= self.curr_low)):
                    self.temp_ret = self.default_reward


        else:
            dt_pos = datetime.datetime.fromtimestamp(self.broker.positions["Ticker"].log[-1].timestamp)
            day_pos = dt_pos.day
            hr = dt.hour
            if (day_pos != day) & (hr >= self.time_cut):
                self.broker.close_position(
                    "Ticker", price=self.broker.data_provider.current("Ticker", "open", timeframe=TimeFrames.Minute))
                if self.temp == len(self.broker.trade_hist_percentage_weighted):
                    raise ValueError
                else:
                    ret = self.broker.trade_hist_percentage_weighted[-1]
                    if ret < 0:
                        ret += self.default_reward
                self.temp = len(self.broker.trade_hist_percentage_weighted)
                return ret

    def convert_reward(self, ret):
        return ret


if __name__ == '__main__':
    k, time_cut, episode_len, default_reward, min_bet, max_leverage = (0.5, 3, 17280000, -0.1, 0.1, 1)

    env_config = {
        "data_path_1min" : [
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/XRPQUT.csv",
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/EOSQUT.csv",
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/LTCQUT.csv",
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/BCHQUT.csv",
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/ADAQUT.csv",
                                           ],

        "data_path_1day": [
                "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/XRPQUT.csv",
                "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/EOSQUT.csv",
                "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/LTCQUT.csv",
                "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/BCHQUT.csv",
                "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/ADAQUT.csv",
                                           ],

        "default_reward" : default_reward,
        "max_leverage": max_leverage,
        "from_timeindex" : -np.inf,
        "to_timeindex" : np.inf,
        "episode_len": episode_len,
        "time_cut" : time_cut,
        "min_bet": min_bet,
        "k" : k,
    }

    env = VBRLEnv_V2(env_config)
    for x in range(1000):
        state = env.reset()
        done = False
        score = 0
        while not done:
            state, reward, done, _ = env.step((np.random.choice([-1, 0, 1]), np.random.uniform()*3))
            score += reward
            print(state, reward, done)
            if done:
                print(score)
                break