import pandas as pd
import datetime
import time
from dateutils import relativedelta
from blqt.backtest.historical_data import TimeIndexedData
import os

def add_close_time(data_path, date_column="timestamp", **kwargs):
    df = pd.read_csv(data_path)
    ts = [datetime.datetime.strptime(x, "%Y-%m-%d") for x in df[date_column].values]
    ts = [t + relativedelta(**kwargs) for t in ts]

    df[date_column] = ts
    print(df.head())
    df.to_csv(data_path)
    
def add_close_time_dir(path, **kwargs):
    fnames = os.listdir(path)
    fnames = list(filter(lambda x: x[-6:] == f"1D.csv", fnames))
    for f in fnames:
        pth = path + f
        add_close_time(pth, **kwargs)

def resample_ohlc(path, export_path, open="open",high="high",low="low",close="close",volume="volume",
                  timestamp="timestamp", period="1H"):
    df = pd.read_csv(path)
    df.index = pd.to_datetime(df[timestamp])
    df = df.resample(period).agg({
        open : "first",
        high : "max",
        low : "min",
        close : "last",
        volume : "sum"
    })

    df = df.fillna(method="ffill")

    df.to_csv(export_path)

def resample_ohlc_dir(path, from_period, to_period, **kwargs):
    fnames = os.listdir(path)
    fnames = list(filter(lambda x: x[-6:] == f"{from_period}.csv", fnames))
    print(fnames)
    for f in fnames:
        pth = path + f
        epth = path + f[:-6] + f"{to_period}.csv"
        resample_ohlc(pth, epth, period=to_period, **kwargs)

def make_bitmex_data(path):
    df = pd.read_csv(path)
    df["timestamp"] = [time.mktime(datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timetuple()) for t in
                       df["timestamp"].tolist()]
    data = TimeIndexedData()
    data.from_pandas(df)

    return data

if __name__ == '__main__':
    resample_ohlc_dir("../../data/bitmex/", "1T", "5T")
    resample_ohlc_dir("../../data/bitmex/", "1T", "10T")