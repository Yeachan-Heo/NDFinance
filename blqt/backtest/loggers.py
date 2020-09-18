import threading
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import datetime
from blqt.backtest.utils import *
import warnings

warnings.filterwarnings(action="ignore")


class Logger(object):
    def __init__(self):
        self.sys = None

    def log(self, *args, **kwargs):
        pass

    def set_system(self, sys):
        self.sys = sys


class CLIAsyncLogger(Logger):
    def __init__(self):
        super(CLIAsyncLogger, self).__init__()
        self.log_queue = []
        self.log_thread = threading.Thread(target=self.log)

    def log(self):
        while self.switch:
            for log in self.log_queue:
                print("[LOG] ", log)
                self.log_queue.remove(log)

    def toggle(self, switch=True):
        self.switch = switch
        if switch is True:
            self.log_thread.start()


class BasicLogger(Logger):
    def __init__(self, benchmark_ticker):
        super(BasicLogger, self).__init__()
        self.benchmark_lst = []
        self.pv_lst = []
        self.timestamp_lst = []
        self.benchmark_ticker = benchmark_ticker

    def set_system(self, sys):
        super(BasicLogger, self).set_system(sys)
        self.timeframe = min(self.sys.data_provider.ohlcv_data[self.benchmark_ticker].keys())

    def log(self):
        self.pv_lst.append(self.sys.broker.pv)
        self.benchmark_lst.append(self.sys.data_provider.current(self.benchmark_ticker, "close", self.timeframe))
        self.timestamp_lst.append(self.sys.broker.indexer.timestamp)

    def make_freq_pnl_str(self, pnl_freq):
        _, arr, best, worse, mean = \
            calc_freq_pnl(pv_lst=self.pv_lst, timestamp_lst=self.timestamp_lst, freq=pnl_freq)
        return f"""
            best {pnl_freq} p&L(%): {np.round(best, 2)}%
            worst {pnl_freq} p&L(%): {np.round(worse, 2)}%
            average {pnl_freq} p&L(%): {np.round(mean, 2)}%
            stddev of {pnl_freq} p&L(%) :{np.round(np.std(arr), 2)}
        """

    def _result(self):
        if self.sys is not None:
            self.trade_hist_rate = self.sys.broker.trade_hist_rate
            self.trade_hist = self.sys.broker.trade_hist
            self.trade_hist_rate_weighted = self.sys.broker.trade_hist_rate_weighted

        self.timestamp_lst = np.array(self.timestamp_lst)
        self.benchmark_lst = np.array(self.benchmark_lst)

        self.pv_lst = np.array(self.pv_lst)
        self.pv_lst = fillna_arr(self.pv_lst, method="ffill")

        self.win_lst = list(filter(lambda x: x > 0, self.trade_hist))
        self.lose_lst = list(filter(lambda x: x < 0, self.trade_hist))

        self.cagr = calc_cagr(self.pv_lst, self.timestamp_lst)

        self.sharpe_ratio, self.sortino_ratio = calc_sharpe_sortino_ratio(self.pv_lst, self.benchmark_lst,
                                                                          self.timestamp_lst)

    def result(self):
        self._result()
        self.trade_hist_rate = np.array(self.trade_hist_rate)
        self.trade_hist_rate_weighted = np.array(self.trade_hist_rate_weighted)
        return (
            f"""
        overall p&L(%): {np.round(self.pv_lst[-1] / self.pv_lst[0] * 100 - 100, 2)}%
        MDD(%): {np.round(get_mdd(self.pv_lst)[-1] * 100, 2)}%
        CAGR(%): {np.round(self.cagr, 2)}%\n

        sharpe ratio: {np.round(self.sharpe_ratio, 2)}
        sortino ratio: {np.round(self.sortino_ratio, 2)}\n

        p&l rate: {np.round(-np.mean(self.win_lst) / np.mean(self.lose_lst), 2)}
        win rate: {np.round(len(self.win_lst) / len(self.trade_hist) * 100, 2)}%
        lose rate: {np.round(len(self.lose_lst) / len(self.trade_hist) * 100, 2)}%\n

        average p&L(%) per trade: {np.round(np.mean(self.trade_hist_rate) * 100, 2)} %
        max p&L(%) per trade: {np.round(np.max(self.trade_hist_rate) * 100, 2)} %
        min p&L(%) per trade: {np.round(np.min(self.trade_hist_rate) * 100, 2)} %
        stddev of p&L(%) per trade: {np.round(np.std(self.trade_hist_rate) * 100, 2)} 

        average p&L(%) per trade(weighted): {np.round(np.mean(self.trade_hist_rate_weighted) * 100, 2)} %
        max p&L(%) per trade(weighted): {np.round(np.max(self.trade_hist_rate_weighted) * 100, 2)} %
        min p&L(%) per trade(weighted): {np.round(np.min(self.trade_hist_rate_weighted) * 100, 2)} %
        stddev of p&L(%) per trade(weighted): {np.round(np.std(self.trade_hist_rate_weighted) * 100, 2)} 

        {self.make_freq_pnl_str("1M")}
            
        {self.make_freq_pnl_str("1D")}

        number of trades:{len(self.trade_hist)}"""
        )

    @staticmethod
    def set_colormap(patches, cm=plt.cm.viridis):
        for i, p in enumerate(patches):
            plt.setp(p, 'facecolor', cm(i / len(patches)))

    def plot_relative(self, rolling_period=60 * 60 * 24 * 365):
        self.fig = plt.figure(figsize=(38.4, 21.6))
        self.gs = plt.GridSpec(nrows=5, ncols=2, height_ratios=np.array([1, 0.25, 0.25, 0.25, 0.25]) * 2)
        self.plot_main()
        self.plot_bars()
        self.plot_histogram()
        self.plot_rolling(rolling_period)
        self.fig.show()

        return self.fig

    def plot_main(self):
        x = [datetime.datetime.fromtimestamp(d) for d in self.timestamp_lst]
        ax_main = self.fig.add_subplot(self.gs[0])
        ax_main.plot(x, (np.array(self.pv_lst) / self.pv_lst[0] - 1) * 100, label="portfolio", color="b", linewidth=2)
        ax_main.plot(x, (np.array(self.benchmark_lst) / self.benchmark_lst[0] - 1) * 100, color="r",
                     label="benchmark", linewidth=2)
        ax_main.set_ylabel("cumulative p&L(%)")
        ax_main.legend()
        return

    def plot_histogram(self):

        daily_timestamp, daily_pnl = calc_freq_pnl(self.pv_lst, self.timestamp_lst, freq="1D")[:2]
        monthly_timestamp, monthly_pnl = calc_freq_pnl(self.pv_lst, self.timestamp_lst, freq="1M")[:2]
        bins_coeff = 5
        ax1 = self.fig.add_subplot(self.gs[3])
        rng = max(np.abs(daily_pnl.max()) * 100, np.abs(daily_pnl.min()) * 100)
        bins = len(daily_pnl) // bins_coeff
        n, b, p = ax1.hist(daily_pnl * 100, label="Daily p&L(%)", range=(-rng, rng), bins=bins)
        self.set_colormap(p)
        ax1.yaxis.set_major_formatter(PercentFormatter(xmax=sum(n)))
        ax1.legend()

        bx1 = self.fig.add_subplot(self.gs[5])
        rng = max(np.abs(monthly_pnl.max()) * 100, np.abs(monthly_pnl.min()) * 100)
        bins = len(monthly_pnl) // bins_coeff
        n, b, p = bx1.hist(monthly_pnl * 100, label="Monthly p&L(%)", range=(-rng, rng), bins=bins)
        self.set_colormap(p)
        bx1.yaxis.set_major_formatter(PercentFormatter(xmax=sum(n)))
        bx1.legend()

        cx1 = self.fig.add_subplot(self.gs[7])
        rng = max(np.abs(self.trade_hist_rate.max()) * 100,
                  np.abs(self.trade_hist_rate.min()) * 100)
        bins = len(self.trade_hist_rate) // bins_coeff
        n, b, p = cx1.hist(self.trade_hist_rate * 100, label="Trade p&L(%)",
                           range=(-rng, rng), bins=bins)
        self.set_colormap(p)
        cx1.yaxis.set_major_formatter(PercentFormatter(xmax=sum(n)))
        cx1.legend()

        cx1 = self.fig.add_subplot(self.gs[9])
        rng = max(np.abs(self.trade_hist_rate_weighted.max()) * 100,
                  np.abs(self.trade_hist_rate_weighted.min()) * 100)
        bins = len(self.trade_hist_rate_weighted) // bins_coeff
        n, b, p = cx1.hist(self.trade_hist_rate_weighted * 100,
                           label="Trade p&L Weighted(%)", range=(-rng, rng), bins=bins)
        self.set_colormap(p)
        cx1.yaxis.set_major_formatter(PercentFormatter(xmax=sum(n)))
        cx1.legend()

        return self.fig

    def plot_rolling(self, rolling_period):
        ax2 = self.fig.add_subplot(self.gs[2])
        timestamp_lst, mdd = get_rolling_mdd(self.pv_lst, self.timestamp_lst, rolling_period)
        ax2.plot(timestamp_lst, mdd, label="MDD", color="#000000", linewidth=3)
        ax2.legend()

        bx2 = self.fig.add_subplot(self.gs[4])
        timestamp_lst, cagr = get_rolling_cagr(self.pv_lst, self.timestamp_lst, rolling_period)
        bx2.plot(timestamp_lst, cagr, label="CAGR", color="#000000", linewidth=3)
        bx2.legend()

        cx2, dx2 = self.fig.add_subplot(self.gs[6]), self.fig.add_subplot(self.gs[8])
        timestamp_lst, sharpe, sortino = get_rolling_sharpe_sortino_ratio(
            self.pv_lst, self.benchmark_lst, self.timestamp_lst, rolling_period
        )

        cx2.plot(timestamp_lst, sharpe, "-.", label="sharpe ratio", color="#000000", linewidth=4)
        cx2.legend()

        dx2.plot(timestamp_lst, sortino, "-.", label="sortino ratio", color="#000000", linewidth=4)
        dx2.legend()

        return self.fig

    def plot_bars(self):
        monthly_timestamp, monthly_pnl = calc_freq_pnl(self.pv_lst, self.timestamp_lst, freq="1M")[:2]
        ax = self.fig.add_subplot(self.gs[1])

        x = np.arange(len(monthly_pnl))
        profit_idx = np.where(monthly_pnl >= 0)
        loss_idx = np.where(monthly_pnl < 0)

        ax.bar(x[profit_idx], monthly_pnl[profit_idx] * 100, color="g")
        ax.bar(x[loss_idx], monthly_pnl[loss_idx] * 100, color="r")
        ax.set_title("monthly p&L(%)")
        ax.set_ylabel("p&L(%)")
        ticks = np.arange(len(monthly_pnl), step=len(monthly_pnl) // 6)

        ax.set_xticks(ticks=ticks)
        ax.set_xticklabels(labels=[str(x)[:7] for x in monthly_timestamp[ticks]])

        return


class LiveLogger(BasicLogger):
    def __init__(self, *args, **kwargs):
        super(LiveLogger, self).__init__(*args, **kwargs)
        plt.ion()

    def plot_relative(self):
        plt.clf()
        plt.plot(self.timestamp_lst, np.array(self.pv_lst) / self.pv_lst[0], label="portfolio")
        plt.plot(self.timestamp_lst, np.array(self.benchmark_lst) / self.benchmark_lst[0], label="benchmark")
        plt.legend()
        plt.pause(1e-20)

    def log(self):
        super(LiveLogger, self).log()
        self.plot_relative()
