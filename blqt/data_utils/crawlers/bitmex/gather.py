import pandas as pd
import os
import multiprocessing
import tqdm
from blqt.data_utils import *


def split_list(alist, wanted_parts=1):
    length = len(alist)
    return [ alist[i*length // wanted_parts: (i+1)*length // wanted_parts]
             for i in range(wanted_parts) ]

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


symbols_usd = ['BCHUSD', 'ETHUSD', 'LTCUSD', 'XBTUSD', 'XRPUSD']
symbols_xbt = ['ADAU20', 'EOSU20']

if __name__ == '__main__':
    a = []
    for symbol in symbols_xbt:
        a.append(("/home/bellmanlabs/Data/bitmex/trade/raw/",
               "/home/bellmanlabs/Data/bitmex/trade/ohlc/",
               symbol, "1T"))
    pool = multiprocessing.Pool(len(symbols_xbt))
    pool.map(gather_wrapper, a)





