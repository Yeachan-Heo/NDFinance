import numpy as np
import pandas as pd
import datetime
import time
def to_timestamp(timestamp):
    return [time.mktime(datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timetuple()) for t in
     timestamp.tolist()]

def sign(a):
    return (a > 0) - (a < 0)

def get_mdd(x):
    """
    MDD(Maximum Draw-Down)
    :return: (peak_upper, peak_lower, mdd rate)
    """
    arr_v = np.array(x)
    peak_lower = np.argmax(np.maximum.accumulate(arr_v) - arr_v)
    peak_upper = np.argmax(arr_v[:peak_lower])
    return peak_upper, peak_lower, (arr_v[peak_lower] - arr_v[peak_upper]) / arr_v[peak_upper]

def calc_freq_pnl(pv_lst, timestamp_lst, freq="1M"):
    df = pd.DataFrame({"pv":pv_lst})
    df.index = pd.DatetimeIndex([
        datetime.datetime.fromtimestamp(d) for d in timestamp_lst
    ])

    df = df["pv"].resample(freq).ohlc().dropna()

    pnl_perc = (df["close"] / df["open"]).values - 1
    max_pnl_perc = np.max(pnl_perc)*100
    min_pnl_perc = np.min(pnl_perc)*100
    mean_pnl_perc = np.mean(pnl_perc)*100

    return pnl_perc, max_pnl_perc, min_pnl_perc, mean_pnl_perc

def calc_cagr(pv_lst, timestamp_lst):
    pnl_perc = calc_freq_pnl(pv_lst, timestamp_lst, freq="1Y")[0]

    temp = 1
    for x in pnl_perc:
        temp *= (x+1)

    cagr = temp ** (1/len(pnl_perc))-1
    return cagr*100


def calc_sharpe_sortino_ratio(pv_lst, benchmark_lst, timestamp_lst):
    index = pd.DatetimeIndex([
        datetime.datetime.fromtimestamp(d) for d in timestamp_lst
    ])

    pv_df = pd.DataFrame({"pv": pv_lst}, index=index)
    bench_df = pd.DataFrame({"benchmark": benchmark_lst}, index=index)
    
    pv_df = pv_df["pv"].resample("1M").ohlc().dropna()
    bench_df = bench_df["benchmark"].resample("1M").ohlc().dropna()

    pv_daily_ret = np.log(pv_df["close"].values / pv_df["open"].values)
    bench_daily_ret = np.log(bench_df["close"].values / bench_df["open"].values)

    sharpe_ratio = (np.mean(pv_daily_ret) - np.mean(bench_daily_ret)) / np.std(pv_daily_ret)
    sortino_ratio = (np.mean(pv_daily_ret) - np.mean(bench_daily_ret)) / \
                    np.std(pv_daily_ret[np.where(np.exp(pv_daily_ret) < 1)])

    return sharpe_ratio, sortino_ratio