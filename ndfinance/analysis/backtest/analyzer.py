import numpy as np

from _collections import OrderedDict
from ndfinance.analysis.backtest import *
from ndfinance.brokers.backtest import PortFolioLogLabel, PnlLogLabel
from pprint import pprint
import pandas as pd
import json
import os


def amm(array, label):
    return {
        f"average_{label}": array.mean(),
        f"max_{label}": array.max(),
        f"min_{label}": array.min(),
    }


class BacktestAnalyzer:
    def __init__(self, log, benchmark=None):
        self.log = log
        self.result = {}

        for key, value in self.log.items():
            self.log[key] = np.array(value)

        if benchmark is None:
            benchmark = np.ones(shape=(len(self.log["timestamp"]),))

        self.result["CAGR"] = calc_cagr(self.log["portfolio_value_total"], self.log["timestamp"])
        self.result["MDD"] = -get_mdd(self.log["portfolio_value"])

        self.result["CAGR_MDD_ratio"] = self.result["CAGR"] / self.result["MDD"]

        self.result["sharpe_ratio"], self.result["sortino_ratio"] = calc_sharpe_sortino_ratio(
            self.log["portfolio_value_total"], benchmark, self.log["timestamp"]
        )

        realized_pnl = log[PnlLogLabel.realized_pnl]

        realized_win, realized_lose = \
            filter_array(lambda x: x > 0, realized_pnl), filter_array(lambda x: x < 0, realized_pnl)

        pnl_percentage_sum = -realized_win.sum() / realized_lose.sum()
        self.result["pnl_percentage_sum"] = pnl_percentage_sum
        pnl_rate = -realized_win.mean() / realized_lose.mean()
        self.result["pnl_rate"] = pnl_rate

        [append_dict(self.result, amm(log[l], l)) for l in PnlLogLabel.lst]
        [append_dict(self.result, amm(log[l], l)) for l in PortFolioLogLabel.lst]

        append_dict(self.result, amm(calc_freq_pnl(
            self.log["portfolio_value"], self.log["timestamp"], freq="1M")*100, label="1M_pnl_percentage"))
        append_dict(self.result, amm(calc_freq_pnl(
            self.log["portfolio_value"], self.log["timestamp"], freq="1D")*100, label="1D_pnl_percentage"))
        append_dict(self.result, amm(calc_freq_pnl(
            self.log["portfolio_value"], self.log["timestamp"], freq="7D")*100, label="1W_pnl_percentage"))

    def print(self):
        print("\n"*1)
        print("-"*25, "[BACKTEST RESULT]", "-"*25)
        for key, value in self.result.items():
            print(f"{key}:{round(value, 3)}")

    def export_result(self, path="./bt_result/", name="result.json"):
        with open(path + name, "w") as f:
            f.write(json.dumps(self.result))

    def export_log(self, path="./bt_result/", name="log.csv"):
        pd.DataFrame(self.log).to_csv(path + name)



