import pandas as pd
import os
import threading


def gather(data_dir, export_path, period, symbol):
    if not os.path.exists(export_path):
        os.makedirs(export_path)

    first = True

    for fname in sorted(os.listdir(data_dir)):
        df = pd.read_csv(data_dir + fname)

        df = df.loc[df["symbol"] == symbol]

        if df.empty: continue

        df.index = pd.to_datetime(df["timestamp"].str.replace("D", " "))


        bar = df["price"].resample(period).ohlc().fillna(method="ffill")
        bar["volume"] = df["size"].resample(period).sum().fillna(0)

        if first:
            bar.to_csv(f"{export_path}{fname}")
            first = False
        else:
            bar.to_csv(f"{export_path}{fname}", header=False)


