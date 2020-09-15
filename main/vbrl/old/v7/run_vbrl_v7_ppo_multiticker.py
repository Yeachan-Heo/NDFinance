from blqt.backtest.data_providers import BacktestDataProvider
from blqt.backtest.historical_data import TimeIndexedData
from blqt.backtest.stratagies import *
from blqt.backtest.brokers import BackTestBroker
from blqt.backtest.loggers import BasicLogger
from blqt.backtest.base import *
from talib import abstract as ta
from blqt.backtest.technical import *
from blqt.rl_envs.vb_env import VBEnv
import ray
import ray.rllib.agents.sac as sac
import ray.rllib.agents.ppo as ppo


def make_data(path):
    df = pd.read_csv(path)
    df["timestamp"] = [time.mktime(datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timetuple()) for t in
                       df["timestamp"].tolist()]
    data = TimeIndexedData()
    data.from_pandas(df)

    return data


def first_test(tickers, data_path_1day_lst, data_path_1min_lst, restore_path, name="bt_result"):
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
        Ticker = FinancialProduct(ticker, 0.0000001, 0.0000001, 0.0004, 1, 1, 1)
        broker.add_ticker(Ticker)

    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBEnv

    config["env_config"] = {
        "data_path_1min": data_path_1min_lst[0],
        "data_path_1day": data_path_1day_lst[0],
        "from_timeindex": -np.inf,
        "to_timeindex": np.inf
    }

    config["framework"] = "tf"
    config["num_workers"] = 1
    config["num_gpus"] = 1

    ray.shutdown()
    ray.init()

    agent = ppo.PPOTrainer(config=config, env=VBEnv)
    agent.restore(restore_path)

    stratagy = VBAgentStratagyV5MT(agent, k=0.5, leverage=1)

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


if __name__ == '__main__':
        n = 3000
        first_test(
            ["XBTUSD","ETHUSD"],
            ["/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/XBTUSD.csv",
             "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/ETHUSD.csv"],

            ["/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/XBTUSD.csv",
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/ETHUSD.csv"],

            f"/home/bellmanlabs/Projects/ray_results/VBEnv_V7/PPO/PPO_VBEnv_V7_0_2020-09-11_08-49-20irdzf9c8/checkpoint_{n}/checkpoint-{n}",
            name=f"/home/bellmanlabs/Projects/log/vbrl_multiticker_v4/{n}")