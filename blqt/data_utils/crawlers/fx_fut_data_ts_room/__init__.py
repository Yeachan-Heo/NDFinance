import pandas as pd
import os
from pprint import pprint as print

def parse(fpath, fname):
    df = pd.read_csv(fpath + fname)
    df["Date"] = df["Date"].str.replace("/", "-")
    df["timestamp"] = [d + t for d, t in zip(df["Date"], df[" Time"])]

    export_name = fname.split("_")[0] + ".csv"

    df = df[["timestamp", " Open", " High", " Low", " Last", " Volume"]]
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    print(fpath + export_name)
    df.to_csv(fpath + export_name)


def parse_dir(target_dir):
    for fname in os.listdir(target_dir):
        parse(target_dir, fname)


if __name__ == '__main__':
    parse_dir("/home/bellmanlabs/Data/FX_FUT_DATA/raw/")
