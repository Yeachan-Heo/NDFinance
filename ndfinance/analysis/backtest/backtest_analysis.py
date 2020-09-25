from ndfinance.utils.array_utils import *
from ndfinance.brokers.base.data_provider import OHLCVT

def make_benchmark(data_provider, from_timestamp, to_timestamp, *args):
    lst = []
    for arg in args:
        timestamp = data_provider["ohlcv"][arg][OHLCVT.timestamp]
        first_index = np.where(from_timestamp<timestamp)[-1][0]
        last_index = np.where(to_timestamp>timestamp)[-1][0]
        close = data_provider["ohlcv"][arg][OHLCVT.close]
        close = np.array(close[first_index:last_index])
        close = close[1:] / close[:-1]
        close = np.array([0] + list(close))
        lst.append(close)
    benchmark = lst[0]
    for e in lst[1:]:
        benchmark += e
    return cummul(benchmark/len(lst))



def get_rolling_mdd(pv_lst, timestamp_lst, period):
    window_size = get_rolling_window_size(timestamp_lst, period)
    timestamp_lst = to_datetime(rolling_window(timestamp_lst, window_size, lambda x: x[-1]))
    mdd_lst = rolling_window(pv_lst, window_size, lambda x: -get_mdd(x))
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
    index = pd.DatetimeIndex([
        datetime.datetime.fromtimestamp(d) for d in timestamp_lst
    ])

    pv_df = pd.DataFrame({"pv": pv_lst}, index=index)
    bench_df = pd.DataFrame({"benchmark": benchmark_lst}, index=index)

    pv_df = pv_df["pv"].resample("1M").ohlc().dropna()
    bench_df = bench_df["benchmark"].resample("1M").ohlc().dropna()

    pv_ret = np.log(pv_df["close"].values / pv_df["open"].values)
    bench_ret = np.log(bench_df["close"].values / bench_df["open"].values)

    timestamp_lst = np.array([x.timestamp() for x in pv_df.index]).flatten()

    window_size = get_rolling_window_size(timestamp_lst, period)
    timestamp_lst = rolling_window(timestamp_lst, window_size, lambda x: x[-1])

    sharpe, sortino = [], []

    for i, (_, _) in enumerate(zip(bench_ret[window_size - 1:], pv_ret[window_size - 1:])):
        be, pv = bench_ret[i:i + window_size], pv_ret[i:i + window_size]
        sharpe_ratio, sortino_ratio = calc_sharpe_sortino_ratio_v2(pv, be)
        sortino.append(sortino_ratio)
        sharpe.append(sharpe_ratio)

    return to_datetime(timestamp_lst), np.array(sharpe), np.array(sortino)


def get_mdd(x):
    """
    MDD(Maximum Draw-Down)
    :return: (peak_upper, peak_lower, mdd rate)
    """
    arr_v = np.array(x)
    peak_lower = np.argmax(np.maximum.accumulate(arr_v) - arr_v)
    peak_upper = np.argmax(arr_v[:peak_lower])
    return (arr_v[peak_lower] - arr_v[peak_upper]) / arr_v[peak_upper] * 100


def calc_freq_pnl(pv_lst, timestamp_lst, freq="1M"):
    df = pd.DataFrame({"pv": pv_lst})
    df.index = pd.DatetimeIndex([
        datetime.datetime.fromtimestamp(d) for d in timestamp_lst
    ])

    df = df["pv"].resample(freq).ohlc().dropna()

    pnl_perc = (df["close"] / df["open"]).values - 1

    return list(df.index), pnl_perc


def calc_cagr(pv_lst, timestamp_lst):
    _, pnl_perc_ld = calc_freq_pnl(pv_lst, timestamp_lst, freq="1D")

    temp = pv_lst[-1] / pv_lst[0]

    cagr = temp ** (1 / (len(pnl_perc_ld) / 365)) - 1
    return cagr * 100


def calc_cagr_v2(pv_lst, n_days):
    temp = pv_lst[-1] / pv_lst[0]
    cagr = temp ** (1 / (n_days / 365)) - 1
    return cagr * 100


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


def calc_sharpe_sortino_ratio_v2(pv_ret, bench_ret):
    sharpe_ratio = (np.mean(pv_ret) - np.mean(bench_ret)) / np.std(pv_ret)
    sortino_ratio = (np.mean(pv_ret) - np.mean(bench_ret)) / \
                    np.std(pv_ret[np.where(np.exp(pv_ret) < 1)])

    return sharpe_ratio, sortino_ratio

