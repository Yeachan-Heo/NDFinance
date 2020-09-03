import numpy as np
import pandas as pd
import datetime
import time
import multiprocessing
import psutil


def split_list(alist, wanted_parts=1):
    length = len(alist)
    return [ alist[i*length // wanted_parts: (i+1)*length // wanted_parts]
             for i in range(wanted_parts) ]


def to_timestamp(timestamp):
    return [time.mktime(datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timetuple()) for t in
     timestamp.tolist()]

def to_datetime(timestamp):
    return [datetime.datetime.fromtimestamp(x) for x in timestamp]

def sign(a):
    return (a > 0) - (a < 0)

def fillna_arr(array, **kwargs):
    df = pd.DataFrame({"v": array})
    df = df.fillna(**kwargs)
    return df["v"].values


def rolling_window(observations, n, func:lambda x: x):
    ret = []
    for i, data in enumerate(observations[n - 1:]):
        strip = func(observations[i:i + n])
        ret.append(strip)
    return np.array(ret)


def get_rolling_window_size(timestamp_lst, period):
    return len(timestamp_lst[np.where(timestamp_lst <= timestamp_lst[0] + period)[0]])

def get_rolling_mdd(pv_lst, timestamp_lst, period):
    window_size = get_rolling_window_size(timestamp_lst, period)
    timestamp_lst = to_datetime(rolling_window(timestamp_lst, window_size, lambda x: x[-1]))
    mdd_lst = rolling_window(pv_lst, window_size, lambda x: -get_mdd(x)[-1]*100)
    mdd_lst = np.array(mdd_lst)
    return timestamp_lst, mdd_lst


def get_rolling_cagr(pv_lst, timestamp_lst, period):
    n_days = period // (60 * 60 * 24)
    window_size = get_rolling_window_size(timestamp_lst, period)
    timestamp_lst = rolling_window(timestamp_lst, window_size, lambda x: x[-1])
    cagr_lst = rolling_window(pv_lst, window_size, lambda x: calc_cagr_v2(x, n_days))
    cagr_lst = np.array(cagr_lst)
    return to_datetime(timestamp_lst), cagr_lst


def get_rolling_sharpe_sortino_ratio(pv_lst, benchmark_lst, timestamp_lst, period):
    window_size = get_rolling_window_size(timestamp_lst, period)
    timestamp_lst = rolling_window(timestamp_lst, window_size, lambda x: x[-1])

    sharpe, sortino = [], []

    scaler = (60*60*24*365 // (timestamp_lst[1] - timestamp_lst[0])) ** 0.5

    for i, (bench, port) in enumerate(zip(benchmark_lst[window_size - 1:], pv_lst[window_size - 1:])):
        be, pv = benchmark_lst[i:i+window_size], pv_lst[i:i+window_size]
        sharpe_ratio, sortino_ratio = calc_sharpe_sortino_ratio_v2(pv, be)
        sharpe.append(sharpe_ratio*scaler)
        sortino.append(sortino_ratio*scaler)

    return to_datetime(timestamp_lst), np.array(sharpe), np.array(sortino)


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
    pnl_perc_ld = calc_freq_pnl(pv_lst, timestamp_lst, freq="1D")[0]

    temp = pv_lst[-1]/pv_lst[0]

    cagr = temp ** (1/(len(pnl_perc_ld)/365)) - 1
    return cagr*100


def calc_cagr_v2(pv_lst, n_days):
    temp = pv_lst[-1]/pv_lst[0]
    cagr = temp ** (1/(n_days/365)) - 1
    return cagr*100


def calc_sharpe_sortino_ratio(pv_lst, benchmark_lst, timestamp_lst):
    index = pd.DatetimeIndex([
        datetime.datetime.fromtimestamp(d) for d in timestamp_lst
    ])

    pv_df = pd.DataFrame({"pv": pv_lst}, index=index)
    bench_df = pd.DataFrame({"benchmark": benchmark_lst}, index=index)
    
    pv_df = pv_df["pv"].resample("1M").ohlc().dropna()
    bench_df = bench_df["benchmark"].resample("1M").ohlc().dropna()

    pv_ret = np.log(pv_df["close"].values / pv_df["open"].values)
    bench_ret = np.log(bench_df["close"].values / bench_df["open"].values)

    sharpe_ratio = (np.mean(pv_ret) - np.mean(bench_ret)) / np.std(pv_ret)
    sortino_ratio = (np.mean(pv_ret) - np.mean(bench_ret)) / \
                    np.std(pv_ret[np.where(np.exp(pv_ret) < 1)])

    return sharpe_ratio, sortino_ratio



def calc_sharpe_sortino_ratio_v2(pv_lst, benchmark_lst):
    pv_ret = np.log(pv_lst[1:] / pv_lst[:-1])
    bench_ret = np.log(benchmark_lst[1:]/benchmark_lst[:-1])

    sharpe_ratio = (np.mean(pv_ret) - np.mean(bench_ret)) / np.std(pv_ret)
    sortino_ratio = (np.mean(pv_ret) - np.mean(bench_ret)) / \
                    np.std(pv_ret[np.where(np.exp(pv_ret) < 1)])

    return sharpe_ratio, sortino_ratio

    