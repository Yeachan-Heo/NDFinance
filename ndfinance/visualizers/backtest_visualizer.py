import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from ndfinance.analysis.backtest.backtest_analysis import *
from ndfinance.utils.array_utils import *
from ndfinance.brokers.base import TimeFrames
import warnings
import ray


warnings.filterwarnings("ignore")

plt.style.use("seaborn")
plt.rcParams["font.size"] = 20

class Visualizer(object):
    def __init__(self):
        self.sys = None

    def get_data(self, *args, **kwargs):
        pass

    def set_system(self, sys):
        self.sys = sys


class BacktestVisualizer(Visualizer):
    def __init__(self, benchmark_ticker):
        super(BacktestVisualizer, self).__init__()
        self.benchmark_lst = []
        self.pv_lst = []
        self.timestamp_lst = []
        self.leverage_lst = []
        self.benchmark_ticker = benchmark_ticker

    def set_system(self, sys):
        super(BacktestVisualizer, self).set_system(sys)
        self.timeframe = min(self.sys.data_provider.ohlcv_data[self.benchmark_ticker].keys())

    def get_data(self):
        self.pv_lst.append(self.sys.broker.pv)
        self.benchmark_lst.append(self.sys.data_provider.current(self.benchmark_ticker, "close", self.timeframe))
        self.timestamp_lst.append(self.sys.broker.indexer.timestamp)
        self.leverage_lst.append(self.sys.broker.leverage)

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
            self.trade_hist_percentage = self.sys.broker.trade_hist_percentage
            self.trade_hist = self.sys.broker.trade_hist
            self.trade_hist_percentage_weighted = self.sys.broker.trade_hist_percentage_weighted

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
        self.trade_hist_percentage = np.array(self.trade_hist_percentage)
        self.trade_hist_percentage_weighted = np.array(self.trade_hist_percentage_weighted)
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

        average p&L(%) per trade: {np.round(np.mean(self.trade_hist_percentage) * 100, 2)} %
        max p&L(%) per trade: {np.round(np.max(self.trade_hist_percentage) * 100, 2)} %
        min p&L(%) per trade: {np.round(np.min(self.trade_hist_percentage) * 100, 2)} %
        stddev of p&L(%) per trade: {np.round(np.std(self.trade_hist_percentage) * 100, 2)} 

        average p&L(%) per trade(weighted): {np.round(np.mean(self.trade_hist_percentage_weighted) * 100, 2)} %
        max p&L(%) per trade(weighted): {np.round(np.max(self.trade_hist_percentage_weighted) * 100, 2)} %
        min p&L(%) per trade(weighted): {np.round(np.min(self.trade_hist_percentage_weighted) * 100, 2)} %
        stddev of p&L(%) per trade(weighted): {np.round(np.std(self.trade_hist_percentage_weighted) * 100, 2)} 

        max leverage: {np.max(self.leverage_lst).round(2)}x

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
        self.plot_hist()
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
        rng = max(np.abs(self.trade_hist_percentage.max()) * 100,
                  np.abs(self.trade_hist_percentage.min()) * 100)
        bins = len(self.trade_hist_percentage) // bins_coeff
        n, b, p = cx1.hist(self.trade_hist_percentage * 100, label="Trade p&L(%)",
                           range=(-rng, rng), bins=bins)
        self.set_colormap(p)
        cx1.yaxis.set_major_formatter(PercentFormatter(xmax=sum(n)))
        cx1.legend()

        cx1 = self.fig.add_subplot(self.gs[9])
        rng = max(np.abs(self.trade_hist_percentage_weighted.max()) * 100,
                  np.abs(self.trade_hist_percentage_weighted.min()) * 100)
        bins = len(self.trade_hist_percentage_weighted) // bins_coeff
        n, b, p = cx1.hist(self.trade_hist_percentage_weighted * 100,
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


def set_colormap(patches, cm=plt.cm.viridis):
    for i, p in enumerate(patches):
        plt.setp(p, 'facecolor', cm(i / len(patches)))

class BasicVisualizer(Visualizer):
    def __init__(self):
        super(BasicVisualizer, self).__init__()

    def plot_hist(self, y, label, xlabel="", ylabel="", fig=None, subplot_loc=111,
                       cmap=plt.cm.viridis, bins_coeff=1, align=False, figsize=(20, 10), *args, **kwargs):
        fig = fig

        if fig is None:
            fig = plt.figure(figsize=figsize, *args, **kwargs)

        ax = fig.add_subplot(subplot_loc)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        if align:
            rng = [max(np.abs(y.max()), np.abs(y.min())) for _ in range(2)]
            bins = len(y) // bins_coeff

            n, b, p = ax.hist(y, label=label, range=rng, bins=bins, *args, **kwargs)
        else:
            n, b, p = ax.hist(y, label=label, *args, **kwargs)

        ax.yaxis.set_major_formatter(PercentFormatter(xmax=np.clip(sum(n), 1, np.inf)))
        
        set_colormap(p, cm=cmap)

        ax.legend()
        return fig

    def plot_line(self, x, y, label, xlabel="", ylabel="", color="#000000", fig=None, subplot_loc=111, figsize=(20, 10), *args, **kwargs):
        fig = fig

        if fig is None:
            fig = plt.figure(figsize=figsize, *args, **kwargs)

        ax = fig.add_subplot(subplot_loc)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        ax.plot(x, y, color=color, label=label, *args, **kwargs)

        ax.legend()

        return fig

    def plot_bar(self, x, y, label, xlabel="", ylabel="", fig=None, subplot_loc=111, xtick_n=6, figsize=(20, 10), *args, **kwargs):
        x, y = np.array(x), np.array(y)
        fig = fig

        if fig is None:
            fig = plt.figure(figsize=figsize, *args, **kwargs)

        ax = fig.add_subplot(subplot_loc)

        ax.set_title(label)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        idxs = np.arange(len(y))
        plus_idx = np.where(y >= 0)
        minus_idx = np.where(y < 0)

        ax.bar(idxs[plus_idx], y[plus_idx], color="g")
        ax.bar(idxs[minus_idx], y[minus_idx], color="r")

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        ax.set_xticklabels(x[np.arange(0, len(x), step=len(x) // xtick_n)])

        return fig

    def plot_log(self, log, rolling_period=TimeFrames.day*365):
        mdd_timestamp_lst, mdd = get_rolling_mdd(log["portfolio_value"], log["timestamp"], period=rolling_period)
        cagr_timestamp_lst, cagr = get_rolling_cagr(log["portfolio_value"], log["timestamp"], period=rolling_period)
        sortino_timestamp_lst, sharpe, sortino = get_rolling_sharpe_sortino_ratio(
            log["portfolio_value"], log["benchmark"], log["timestamp"], period=rolling_period
        )

        self.rolling_dict = {
            "mdd" : mdd,
            "cagr": cagr,
            "sharpe": sharpe,
            "sortino": sortino,
        }

        log["datetime"] = to_datetime(log["timestamp"])
        log["datetime_str"] = [str(x)[:7] for x in log["datetime"]]

        self.fig_dict = {
            "mdd": self.plot_line(
                mdd_timestamp_lst, self.rolling_dict["mdd"],
                label="MDD(%)", xlabel="date", ylabel="MDD(%)"
            ),
            "cagr": self.plot_line(
                cagr_timestamp_lst, self.rolling_dict["cagr"],
                label="CAGR(%)", xlabel="date", ylabel="CAGR(%)"
            ),
            "sharpe": self.plot_line(
                sortino_timestamp_lst, self.rolling_dict["sharpe"],
                label="sharpe", xlabel="date", ylabel="sharpe"
            ),
            "sortino": self.plot_line(
                sortino_timestamp_lst, self.rolling_dict["sortino"],
                label="sortino", xlabel="date", ylabel="sortino"
            ),
            "portfolio_value":self.plot_line(
                log["datetime"], log["portfolio_value"],
                label="portfolio_value", xlabel="date", ylabel="portfolio value"
            ),
            "portfolio_value_cum_pnl_perc" : self.plot_line(
                log["datetime"], (log["portfolio_value"] / log["portfolio_value"][0] - 1)*100,
                label="portfolio_value", xlabel="date", ylabel="cumulative p&L(%)"
            ),
            "portfolio_value_total": self.plot_line(
                log["datetime"], log["portfolio_value_total"],
                label="portfolio_value_total", xlabel="date", ylabel="portfolio value"
            ),
            "portfolio_value_total_cum_pnl_perc": self.plot_line(
                log["datetime"], (log["portfolio_value_total"] / log["portfolio_value_total"][0] - 1)*100,
                label="portfolio_value_total", xlabel="date", ylabel="cumulative p&L(%)"
            ),
            "realized_pnl_percentage_hist": self.plot_hist(
                log["realized_pnl_percentage"], label="realized P&L", xlabel="P&L(%)", ylabel="weight(%)"
            ),
            "realized_pnl_percentage_weighted_hist": self.plot_hist(
                log["realized_pnl_percentage_weighted"], label="realized P&L weighted", xlabel="P&L(%)", ylabel="weight(%)"
            ),
            "1M_pnl_hist" : self.plot_hist(
                calc_freq_pnl(log["portfolio_value"], log["timestamp"], "1M")[-1]*100,
                label="1M P&L", xlabel="P&L(%)", ylabel="weight(%)"
            ),
            "1D_pnl_hist": self.plot_hist(
                calc_freq_pnl(log["portfolio_value"], log["timestamp"], "1D")[-1] * 100,
                label="1D P&L(%)", xlabel="P&L(%)", ylabel="weight(%)"
            ),
            "1W_pnl_hist": self.plot_hist(
                calc_freq_pnl(log["portfolio_value"], log["timestamp"], "1W")[-1] * 100,
                label="1W P&L(%)", xlabel="P&L(%)", ylabel="weight(%)"
            ),
            "1M_pnl_bar" : self.plot_bar(
                log["datetime_str"], calc_freq_pnl(log["portfolio_value"], log["timestamp"], "1M")[-1]*100,
                label="1M P&L", xlabel="date", ylabel="P&L(%)"
            ),
            "1D_pnl_bar": self.plot_bar(
                log["datetime_str"], calc_freq_pnl(log["portfolio_value"], log["timestamp"], "1D")[-1] * 100,
                label="1D P&L(%)",  xlabel="date", ylabel="P&L(%)"
            ),
            "1W_pnl_bar": self.plot_bar(
                log["datetime_str"], calc_freq_pnl(log["portfolio_value"], log["timestamp"], "1W")[-1] * 100,
                label="1W P&L(%)",  xlabel="date", ylabel="P&L(%)"
            ),
        }
    def export(self, path="./bt_results/", dpi=100, **export_kwargs):
        print("\n")
        print("-"*50, "[EXPORTING FIGURES]", "-"*50)
        path = path + "plot/"
        if not os.path.exists(path):
            os.makedirs(path)
        for key, value in self.fig_dict.items():
            print("exporting figure to: ", path + key + ".png")
            value.savefig(path + key + ".png", dpi=100, **export_kwargs)
            del value















