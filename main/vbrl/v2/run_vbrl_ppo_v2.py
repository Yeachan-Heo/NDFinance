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


def first_test(data_path_1day, data_path_1min, restore_path):


    initial_margin = 10000000

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

    indexer = TimeIndexer(data_1min["timestamp"],
                               from_timestamp=np.clip(data_1day["timestamp"][20], -np.inf, np.inf),
                               to_timestamp=np.clip(data_1day["timestamp"][-30], -np.inf, np.inf))

    data_provider = BacktestDataProvider()
    data_provider.register_time_indexer(indexer)

    data_provider.register_ohlcv_data("Ticker", data_1min, timeframe=TimeFrames.Minute)
    data_provider.register_ohlcv_data("Ticker", data_1day, timeframe=TimeFrames.Day)

    broker = BackTestBroker(data_provider, indexer)
    broker.initialize(margin=initial_margin)

    Ticker = FinancialProduct("Ticker", 0.25, 4, 0.0003, 0.1, 0.9, 0.000001)
    broker.add_ticker(Ticker)

    config = ppo.DEFAULT_CONFIG.copy()
    config["env"] = VBEnv

    config["env_config"] = {
        "data_path_1min" : data_path_1min,
        "data_path_1day": data_path_1day,
        "from_timeindex" : -np.inf,
        "to_timeindex" : np.inf
    }

    config["framework"] = "torch"
    config["num_workers"] = 2
    
    ray.shutdown()
    ray.init()

    agent = ppo.PPOTrainer(config=config, env=VBEnv)
    agent.restore(restore_path)

    stratagy = VBAgentStratagyV2(agent)

    logger = BasicLogger("Ticker")

    system = BacktestSystem()
    system.set_broker(broker)
    system.set_data_provider(data_provider)
    system.set_logger(logger)
    system.set_stratagy(stratagy)

    system.run()
    system.result()
    broker.calc_pv()
    system.plot()






if __name__ == '__main__':
    for i in range(4, 5):
        n = i * 100
        first_test(
        "/tmp/pycharm_project_716/data/bitmex/ETHUSD_1D.csv",
        "/tmp/pycharm_project_716/data/bitmex/ETHUSD_1H.csv",
        f"/tmp/pycharm_project_716/main/vbrl/v2/log/PPO/PPO_VBEnv_V2_0_2020-08-30_18-36-17m62b6z_y/checkpoint_{n}/checkpoint-{n}")