import pandas as pd
import datetime

import quantstats as qs

def make_daily_ret_df(pv_lst, timestamp_lst, freq="1D"):
    df = pd.DataFrame({"pv": pv_lst})
    df.index = pd.DatetimeIndex([
        datetime.datetime.fromtimestamp(d) for d in timestamp_lst
    ])

    df = df["pv"].resample(freq).ohlc()
    
    df.fillna(0)

    pnl_perc = (df["close"][1:].values / df["close"][:-1].values) - 1

    ret = pd.Series([0] + list(pnl_perc), index=df.index)

    return ret


def report(func):
    def wrapped(log, *args, **kwargs):
        daily_ret_df = make_daily_ret_df(log["portfolio_value_total"], log["timestamp"])
        return func(daily_ret_df, *args, **kwargs)
    return wrapped

make_html = report(qs.reports.html)
make_full = report(qs.reports.full)