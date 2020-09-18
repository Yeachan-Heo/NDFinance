from blqt.backtest.data_providers import BacktestDataProvider
from blqt.backtest.historical_data import TimeIndexedData
from blqt.backtest.stratagies.mean_reversion import RSI2Stratagy
from blqt.backtest.brokers import BackTestBroker
from blqt.backtest.base import *
from blqt.backtest.technical import *
from blqt.rl_envs.vb_env import VBRLEnv
from blqt.backtest.loggers import BasicLogger

import ray
import ray.rllib.agents.ppo as ppo


def make_data(path):
    df = pd.read_csv(path)
    df["timestamp"] = [time.mktime(datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timetuple()) for t in
                       df["timestamp"].tolist()]
    data = TimeIndexedData()
    data.from_pandas(df)

    return data


def first_test(tickers, data_path_1day_lst, data_path_1min_lst, name="bt_results"):


    initial_margin = 100000

    data_provider = BacktestDataProvider()

    ts_lst = None

    for ticker, data_path_1min, data_path_1day in zip(tickers, data_path_1min_lst, data_path_1day_lst):
        data_1min = make_data(data_path_1min)
        data_1day = make_data(data_path_1day)

        data_1day.add_array("RSI2", ta.RSI(data_1day["close"], timeperiod=14))

        data_provider.register_ohlcv_data(ticker, data_1min, timeframe=TimeFrames.Minute)
        data_provider.register_ohlcv_data(ticker, data_1day, timeframe=TimeFrames.Hour)

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
        Ticker = FinancialProduct(ticker, 1, 1, 0, 1, 1, 1)
        broker.add_ticker(Ticker)


    stratagy = RSI2Stratagy(time_cut=TimeFrames.Day, rsi_2_threshold=30)

    logger = BasicLogger(tickers[0])

    system = DistributedBacktestSystem(name=name, n_cores=1)
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
    first_test(
        [
            "ETH",
            "XBT",
        ],

        [
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/ETHUSD.csv",
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1D/XBTUSD.csv",
        ],
        [
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/ETHUSD.csv",
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/XBTUSD.csv",
        ])