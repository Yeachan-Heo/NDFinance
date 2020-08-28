from blqt.backtest.data_providers import BacktestDataProvider
from blqt.backtest.historical_data import TimeIndexedData
from blqt.backtest.stratagies import *
from blqt.backtest.brokers import BackTestBroker
from blqt.backtest.loggers import BasicLogger
from blqt.backtest.base import *
from talib import abstract as ta


def first_test(data_path_1d, data_path_1min):
    df = pd.read_csv(data_path_1d)
    df.columns = [c.lower() for c in df.columns]

    df["timestamp"] = to_timestamp(df["timestamp"])

    data = TimeIndexedData()
    data.from_pandas(df)

    data.add_array("MA20", ta.SMA(df["close"], timeperiod=20))
    data.add_array("MA5", ta.SMA(df["close"], timeperiod=5))
    data.add_array("RSI", ta.RSI(df["close"], timeperiod=14))
    data.add_array("ROCR", ta.ROCR(df["close"], timeperiod=14))
    data.add_array("RANGE", df["high"].values - df["low"].values)
    
    df_1min = pd.read_csv(data_path_1min)
    df_1min["timestamp"] = to_timestamp(df_1min["timestamp"])
    data_1min = TimeIndexedData()
    data_1min.from_pandas(df_1min)

    indexer = TimeIndexer(df_1min["timestamp"].values,
                          from_timestamp=df["timestamp"].values[0],
                          to_timestamp=df_1min["timestamp"].values[-1])

    data_provider = BacktestDataProvider()
    data_provider.register_time_indexer(indexer)

    data_provider.register_ohlcv_data("XBTUSD", data_1min, timeframe=TimeFrames.Minute)
    data_provider.register_ohlcv_data("XBTUSD", data, timeframe=TimeFrames.Day)

    broker = BackTestBroker(data_provider, indexer)
    broker.initialize(margin=10000000)

    NQ = FinancialProduct("XBTUSD", 0.25, 4, 0.0003, 0.1, 0.9, 0.000001)

    broker.add_ticker(NQ)

    system = DistributedBacktestSystem(n_cores=25)

    stratagy = VBFilterAdjustedLongShort("XBTUSD", k=0.6, leverage=1)

    logger = BasicLogger("XBTUSD")

    system.set_broker(broker)
    system.set_data_provider(data_provider)
    system.set_logger(logger)
    system.set_stratagy(stratagy)
    system.run()

    system.result()
    system.plot()


if __name__ == '__main__':
    first_test("../data/XBTUSD_20150925-20200806_1day.csv", "../data/XBTUSD_20150925-20200806_5min.csv")