import pandas as pd
import datetime
import time
from dateutils import relativedelta
import os

def resample_tick(df, symbol, period="1T"):

    df = df.loc[df["symbol"] == symbol]

    if df.empty:
        return df

    df.index = pd.to_datetime(df["timestamp"].str.replace("D", " "))

    bar = df["price"].resample(period).ohlc().fillna(method="ffill")
    bar["volume"] = df["size"].resample(period).sum().fillna(0)

    return bar

def add_close_time(data_path, date_column="timestamp", **kwargs):
    df = pd.read_csv(data_path)
    ts = [datetime.datetime.strptime(x, "%Y-%m-%d") for x in df[date_column].values]
    ts = [t + relativedelta(**kwargs) for t in ts]

    df[date_column] = ts
    print(df.head())
    df.to_csv(data_path)
    
def add_close_time_dir(path, **kwargs):
    fnames = os.listdir(path)
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

def resample_ohlc_dir(path, from_period, to_period, epath=None, **kwargs):
    if epath is None:
        epath = path
    fnames = os.listdir(path)
    for f in fnames:
        pth = path + f
        epth = epath + f
        print(epth)
        resample_ohlc(pth, epth, period=to_period, **kwargs)

if __name__ == '__main__':
    for period in ("3T", "5T", "10T", "15T", "30T", "1H", "1D", "1M", "1Y"):
        resample_ohlc_dir(path="/home/bellmanlabs/Data/FX_FUT_DATA/1T/",
                  epath=f"/home/bellmanlabs/Data/FX_FUT_DATA/{period}/", from_period="1T", to_period=period)
    add_close_time_dir("/home/bellmanlabs/Data/FX_FUT_DATA/1D/", hours=23, minutes=59, seconds=59)