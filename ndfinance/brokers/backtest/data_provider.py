from ndfinance.brokers.base.data_provider import DataProvider, OHLCVT
from ndfinance.analysis.technical import TechnicalIndicator
from ndfinance.brokers.base import TimeIndexer
from ndfinance.utils import array_utils
from ndfinance.brokers.base import TimeFrames, asset
from ndfinance.data.crawlers import get_yf_ticker_async
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import ray


class BacktestDataProvider(DataProvider):
    def __init__(self, primary_timeframe=TimeFrames.day):
        super(BacktestDataProvider, self).__init__()
        self.root = array_utils.StructureDataset()

        self.group_ohlcv = self.root.create_group("ohlcv")
        self.group_fundamental = self.root.create_group("fundamental")

        self.primary_timeframe = primary_timeframe

    def add_ohlc_dataframe(self,
                           df:pd.DataFrame,
                           ticker:str,
                           datetime_format="%Y-%m-%d %H:%M:%S",
                           timeframe=TimeFrames.day,
                           timestamp=OHLCVT.timestamp,
                           open=OHLCVT.open, high=OHLCVT.high,
                           low=OHLCVT.low, close=OHLCVT.close,
                           volume=OHLCVT.volume):
        
        if df.empty:
            warnings.warn("empty df occured")
            return

        if not df[timestamp].values.dtype == np.float64:
            df[timestamp] = array_utils.to_timestamp(df[timestamp], pattern=datetime_format)

        ticker_grp = self.group_ohlcv.create_group(ticker) \
            if not ticker in self.group_ohlcv.keys() else self.group_ohlcv[ticker]
        timeframe_grp = ticker_grp.create_group(timeframe)

        timeframe_grp.create_dataset(name=OHLCVT.timestamp, data=df[timestamp].values)
        timeframe_grp.create_dataset(name=OHLCVT.open, data=df[open].values)
        timeframe_grp.create_dataset(name=OHLCVT.high, data=df[high].values)
        timeframe_grp.create_dataset(name=OHLCVT.low, data=df[low].values)
        timeframe_grp.create_dataset(name=OHLCVT.close, data=df[close].values)
        timeframe_grp.create_dataset(name=OHLCVT.volume, data=df[volume].values)

    def add_ohlc_dataframes(self,
                           dataframes_or_paths,
                           tickers,
                           datetime_format="%Y-%m-%d %H:%M:%S",
                           timeframe=TimeFrames.day,
                           timestamp=OHLCVT.timestamp,
                           open=OHLCVT.open, high=OHLCVT.high,
                           low=OHLCVT.low, close=OHLCVT.close,
                           volume=OHLCVT.volume):

        for df, ticker in zip(dataframes_or_paths, tickers):
            if isinstance(df, str):
                df = pd.read_csv(df)
            self.add_ohlc_dataframe(
                df, ticker, datetime_format, timeframe, timestamp, open, high, low, close, volume)

    def set_indexer(self, indexer:TimeIndexer):
        self.indexer = indexer

    def add_fundamental_dataframe(self, df, ticker, datetime_format="%Y-%m-%d %H:%M:%S", timestamp=OHLCVT.timestamp):
        if not df[timestamp].values.dtype == np.float64:
            df[timestamp] = array_utils.to_timestamp(df[timestamp], pattern=datetime_format)

        ticker_grp = self.group_fundamental.create_group(ticker) \
            if not ticker in self.group_fundamental[ticker] else self.group_fundamental[ticker]
        ticker_grp.create_dataset(name=OHLCVT.timestamp, data=df[timestamp].values)

        for l in list(df.columns):
            ticker_grp.create_dataset(name=l, data=df[l].values)

    def add_fundamental_dataframes(self,
                           dataframes_or_paths,
                           tickers,
                           datetime_format="%Y-%m-%d %H:%M:%S",
                           timestamp=OHLCVT.timestamp):

        for df, ticker in zip(dataframes_or_paths, tickers):
            if isinstance(df, str):
                df = pd.read_csv(df)
            self.add_fundamental_dataframe(
                df, ticker, datetime_format, timestamp)

    def current_price(self, ticker) -> np.ndarray:
        return self.get_ohlcvt(ticker, timeframe=self.primary_timeframe, label=OHLCVT.close)[-1]

    def get_ohlcvt(self, ticker, label, timeframe=None, n=1) -> np.ndarray:
        if isinstance(ticker, asset.Asset):
            ticker = ticker.ticker
        if timeframe is None:
            timeframe = self.primary_timeframe
        idx = np.where(
            self.group_ohlcv[ticker][timeframe][OHLCVT.timestamp] <= self.indexer.timestamp)[-1][-1]
        return self.group_ohlcv[ticker][timeframe][label][:idx][-n:]

    def _add_technical_indicator(self, ticker, timeframe, indicator:TechnicalIndicator):
        self.group_ohlcv[ticker][timeframe].create_dataset(
            indicator.name, indicator(self.group_ohlcv[ticker][timeframe]))

    def add_technical_indicators(self, tickers, timeframes, indicators):
        if not isinstance(tickers, list):
            tickers = [tickers]
        if not isinstance(timeframes, list):
            timeframes = [timeframes]
        if not isinstance(indicators, list):
            indicators = [indicators]

        for ticker in tickers:
            for timeframe in timeframes:
                for indicator in indicators:
                    self._add_technical_indicator(ticker, timeframe, indicator)


    def get_shortest_timestamp_seq(self):
        timeframe_len = np.inf
        timeframe = None
        for ticker in self.group_ohlcv.keys():
            if timeframe_len > len(self.group_ohlcv[ticker][self.primary_timeframe][OHLCVT.timestamp]):
                timeframe = self.group_ohlcv[ticker][self.primary_timeframe][OHLCVT.timestamp]
                timeframe_len = len(timeframe)
        return timeframe

    def add_yf_tickers(self, *tickers):
        dataframes = get_yf_ticker_async(*tickers)
        self.add_ohlc_dataframes(dataframes, tickers)

    def cut_data(self, slip=2):
        for ticker, timeframe_grp in self.group_ohlcv.items():
            for timeframe, label_grp in timeframe_grp.items():
                timestamp = self.group_ohlcv[ticker][timeframe][OHLCVT.timestamp]
                index = np.where((timestamp >= self.indexer.first_timestamp) & (timestamp <= self.indexer.last_timestamp))[-1]
                for label, array in label_grp.items():
                    self.group_ohlcv[ticker][timeframe][label] = self.group_ohlcv[ticker][timeframe][label][int(np.clip(index[0]-slip, 0, np.inf)):int(index[-1])]










