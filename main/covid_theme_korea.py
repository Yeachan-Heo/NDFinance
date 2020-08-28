import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import datetime
import time

from blqt.backtest.data_providers import BacktestDataProvider
from blqt.backtest.historical_data import TimeIndexedData
from blqt.backtest.stratagies import *
from blqt.backtest.brokers import BackTestBroker
from blqt.backtest.loggers import BasicLogger
from blqt.backtest.base import *
from talib import abstract as ta
import yfinance as yf

def download_data(ticker_str, start="2020-03-19"):
    ticker = yf.Ticker(ticker_str)
    df = ticker.history(period="max", start=start)
    df.columns = [c.lower() for c in df.columns]
    df["timestamp"] = [time.mktime(datetime.datetime.strptime(str(t), "%Y-%m-%d %H:%M:%S").timetuple()) for t in
                       df.index.tolist()]
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    return df

codes = [

]

def main():
    code_df = pd.read_csv("../data/covid_theme_companies.csv")

    data_provider = BacktestDataProvider()

    timestamp_lst = [0]*1000000

    available_code_lst = []

    code_lst = code_df["종목코드"].tolist() + ["^KS11"]

    for code in code_lst:
        data = TimeIndexedData()
        df = download_data(code)

        if len(df.index) < 100:

            continue

        available_code_lst.append(code)

        data.from_pandas(df)

        if len(df["timestamp"].tolist()) < len(timestamp_lst):
            timestamp_lst = df["timestamp"].tolist()

        data_provider.register_ohlcv_data(code, data)

    indexer = TimeIndexer(timestamp_lst)
    data_provider.register_time_indexer(indexer)

    broker = BackTestBroker(data_provider, indexer)
    broker.initialize(margin=1000000000)

    for code in available_code_lst:
        product = FinancialProduct(code, 1, 1, 0, 1, 1, 1)
        broker.add_ticker(product)

    system = BacktestSystem()

    stratagy = SmaCrossTrend()

    logger = BasicLogger("^KS11")

    system.set_broker(broker)
    system.set_data_provider(data_provider)
    system.set_logger(logger)
    system.set_stratagy(stratagy)
    system.run()

    logger.result()
    logger.plot_relative()

if __name__ == '__main__':
    main()


