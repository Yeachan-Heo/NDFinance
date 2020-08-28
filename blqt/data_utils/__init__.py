import pandas as pd
import datetime
from dateutils import relativedelta

def add_close_time(data_path, date_column="timestamp", **kwargs):
    df = pd.read_csv(data_path)
    ts = [datetime.datetime.strptime(x, "%Y-%m-%d") for x in df[date_column].values]
    ts = [t + relativedelta(**kwargs) for t in ts]
    df[date_column] = ts
    df.to_csv(data_path)

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
    df.to_csv(export_path)

if __name__ == '__main__':
    resample_ohlc("../../data/XBTUSD_20150925-20200806_1min.csv", "../../data/XBTUSD_20150925-20200806_1hour.csv")