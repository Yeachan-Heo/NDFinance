from blqt.backtest.data_providers import BacktestDataProvider
from blqt.backtest.historical_data import TimeIndexedData
from blqt.backtest.stratagies.VBRL import VBAgentStratagyMT
from blqt.backtest.brokers import BackTestBroker
from blqt.backtest.base import *
from blqt.backtest.technical import *
from blqt.rl_envs.vb_env import VBRLEnv
from blqt.backtest.loggers import BasicLogger

import ray
import ray.rllib.agents.ppo as ppo


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

def first_test(tickers, universe, data_path_1day_lst, data_path_1min_lst, k, time_cut, default_reward, min_bet, max_leverage, ckpt_n=500, name="/home/bellmanlabs/Data/Projects/bt_results/VBRL/"):
    dir_name = listdirs(f"/home/bellmanlabs/Data/Projects/ray_results/VBRL/{k}_{time_cut}_{default_reward}_{min_bet}_{max_leverage}/PPO/")[-1]
    restore_path = f"{dir_name}/checkpoint_{ckpt_n}/checkpoint-{ckpt_n}"
    name = name + f"{k}_{time_cut}_{default_reward}_{min_bet}_{max_leverage}"
    initial_margin = 10000

    data_provider = BacktestDataProvider()

    ts_lst = None

    for ticker, data_path_1min, data_path_1day in zip(tickers, data_path_1min_lst, data_path_1day_lst):
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

        data_provider.register_ohlcv_data(ticker, data_1min, timeframe=TimeFrames.Minute)
        data_provider.register_ohlcv_data(ticker, data_1day, timeframe=TimeFrames.Day)

        if ts_lst is None:
            ts_lst = data_1min["timestamp"]
            from_timestamp = data_1day["timestamp"][20]
            to_timestamp = data_1day["timestamp"][-2]
        else:
            if len(data_1min["timestamp"]) < len(ts_lst):
                ts_lst = data_1min["timestamp"]
                from_timestamp = data_1day["timestamp"][20]
                to_timestamp = data_1day["timestamp"][-2]


    indexer = TimeIndexer(ts_lst, from_timestamp, to_timestamp)

    data_provider.register_time_indexer(indexer)

    broker = BackTestBroker(data_provider, indexer, use_withdraw=False)
    broker.initialize(margin=initial_margin)

    for ticker in tickers:
        Ticker = FinancialProduct(ticker, 1, 1, 0.0004, 1, 1, 1)
        broker.add_ticker(Ticker)

    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBRLEnv

    config["env_config"] = {

        "data_path_1min" : data_path_1min_lst,

        "data_path_1day": data_path_1day_lst,

        "default_reward" : default_reward,
        "max_leverage": max_leverage,
        "from_timeindex" : -np.inf,
        "to_timeindex" : np.inf,
        "episode_len": TimeFrames.Day*200,
        "time_cut" : time_cut,
        "min_bet": min_bet,
        "k" : k,

    }

    config["framework"] = "tf"
    config["num_workers"] = 1
    config["num_gpus"] = 1

    ray.shutdown()
    ray.init(memory=1024*1024*1000, redis_port=8266)

    agent = ppo.PPOTrainer(config=config, env=VBRLEnv)
    agent.restore(restore_path)

    stratagy = VBAgentStratagyMT(agent, k=k, min_bet=min_bet, max_leverage=max_leverage, time_cut=time_cut, universe=universe)

    logger = BasicLogger(tickers[0])

    system = BacktestSystem(name=name)
    system.set_broker(broker)
    system.set_data_provider(data_provider)
    system.set_logger(logger)
    system.set_stratagy(stratagy)

    system.run()
    system.result()
    broker.calc_pv()
    system.plot()

    system.save()

import gc

if __name__ == '__main__':
    cfgs = []
    episode_len = TimeFrames.Day * 200

    for k in [0.5, 0.6, 0.7]:
        for time_cut in [3, 9, 15]:
            for default_reward in [-0.03, -0.05, -0.1]:
                for min_bet in [0, 0.2]:
                    for max_leverage in [1, 3]:
                        cfgs.append((k, time_cut, episode_len, default_reward, min_bet, max_leverage))

    for cfg in reversed(cfgs):
        k, time_cut, episode_len, default_reward, min_bet, max_leverage = cfg

        try:
            first_test(
                [
                    "XRP",
                    "EOS",
                    "LTC",
                    "ETH",
                    "BCH",
                ],
                None,
                [
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/XRPQUT.csv",
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/EOSQUT.csv",
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/LTCQUT.csv",
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/ETHQUT.csv",
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/BCHQUT.csv"
                ],

                [
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/XRPQUT.csv",
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/EOSQUT.csv",
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/LTCQUT.csv",
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/ETHQUT.csv",
                    "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/BCHQUT.csv"
                ],

                k, time_cut, default_reward, min_bet, max_leverage)
            gc.collect()
        except:
            continue