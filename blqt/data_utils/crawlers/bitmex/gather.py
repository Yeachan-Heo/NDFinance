import pandas as pd
import os
import multiprocessing
import tqdm

def split_list(alist, wanted_parts=1):
    length = len(alist)
    return [ alist[i*length // wanted_parts: (i+1)*length // wanted_parts]
             for i in range(wanted_parts) ]

def resample_tick(args):
    data_dir, fname, period, symbol = args
    df = pd.read_csv(data_dir + fname)

    df = df.loc[df["symbol"] == symbol]

    if df.empty:
        return df

    df.index = pd.to_datetime(df["timestamp"].str.replace("D", " "))

    bar = df["price"].resample(period).ohlc().fillna(method="ffill")
    bar["volume"] = df["size"].resample(period).sum().fillna(0)

    return bar

def _gather_wrapper(args):
    return _gather(*args)

def _gather(data_dir, fname, period, symbol):
    df = pd.DataFrame()
    for f in tqdm.tqdm(fname, desc=symbol):
        b = resample_tick([data_dir, f, period, symbol])
        if b.empty:
            continue
        df = df.append(b)
    return df

def gather_wrapper(args):
    return gather(*args)

def gather(data_dir, export_path, symbol, period="1T"):
    if not os.path.exists(export_path):
        os.makedirs(export_path)

    df = _gather(data_dir, os.listdir(data_dir), period, symbol)

    df.to_csv(export_path + f"{symbol}_{period}.csv")


symbols = ['BCHUSD', 'ETHUSD', 'LTCUSD', 'XBTUSD', 'XRPUSD']

if __name__ == '__main__':
    a = []
    for symbol in symbols:
        a.append(("/home/bellmanlabs/Data/bitmex/trade/raw/",
               "/home/bellmanlabs/Data/bitmex/trade/ohlc/",
               symbol, "1T"))
    pool = multiprocessing.Pool(len(symbols))
    pool.map(gather_wrapper, a)





