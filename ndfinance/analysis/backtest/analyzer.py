import numpy as np

from _collections import OrderedDict
from ndfinance.analysis.backtest import *
from ndfinance.brokers.backtest import PortFolioLogLabel, PnlLogLabel
from pprint import pprint
import pandas as pd
import json
import os


def amm(array:np.ndarray, label):
    try:
        if len(array) == 0:
            array = np.zeros(1)
        return {
        f"average_{label}": array.mean(),
        f"max_{label}": array.max(),
        f"min_{label}": array.min(),
        }
    except:
        print(array, label)


class BacktestAnalyzer:
    def __init__(self, log, benchmark=None):
        self.log = log
        self.result = {}

        for key, value in self.log.items():
            self.log[key] = np.array(value)

        if benchmark is None:
            benchmark = np.ones(shape=(len(self.log["timestamp"]),))
            self.log["benchmark"] = benchmark

        self.result["CAGR"] = calc_cagr(self.log["portfolio_value_total"], self.log["timestamp"])
        self.result["MDD"] = -get_mdd(self.log["portfolio_value"])

        self.result["CAGR_MDD_ratio"] = self.result["CAGR"] / self.result["MDD"]

        self.result["win_trade_count"] = len(filter_array(lambda x: x > 0, log["realized_pnl"]))
        self.result["lose_trade_count"] = len(filter_array(lambda x: x < 0, log["realized_pnl"]))

        self.result["total_trade_count"] = len(log["realized_pnl"])

        self.result["win_rate_percentage"] = self.result["win_trade_count"] / np.clip(self.result["total_trade_count"], 1, np.inf) * 100
        self.result["lose_rate_percentage"] = self.result["lose_trade_count"] / np.clip(self.result["total_trade_count"], 1, np.inf) * 100

        self.result["sharpe_ratio"], self.result["sortino_ratio"] = calc_sharpe_sortino_ratio(
            self.log["portfolio_value_total"], benchmark, self.log["timestamp"]
        )

        realized_pnl = log[PnlLogLabel.realized_pnl]

        realized_win, realized_lose = \
            filter_array(lambda x: x > 0, realized_pnl), filter_array(lambda x: x < 0, realized_pnl)

        pnl_ratio_sum = -realized_win.sum() / realized_lose.sum()
        self.result["pnl_ratio_sum"] = pnl_ratio_sum
        pnl_ratio = -realized_win.mean() / realized_lose.mean()
        self.result["pnl_ratio"] = pnl_ratio

        append_dict_lst = PnlLogLabel.lst + PortFolioLogLabel.lst

        for x in [PnlLogLabel.order_timestamp, PnlLogLabel.order_type, OHLCVT.timestamp]:
            append_dict_lst.pop(append_dict_lst.index(x))

        [append_dict(self.result, amm(self.log[x], x)) for x in append_dict_lst]

        append_dict(self.result, amm(calc_freq_pnl(
            self.log["portfolio_value"], self.log["timestamp"], freq="1M")[-1]*100, label="1M_pnl_percentage"))
        append_dict(self.result, amm(calc_freq_pnl(
            self.log["portfolio_value"], self.log["timestamp"], freq="1D")[-1]*100, label="1D_pnl_percentage"))
        append_dict(self.result, amm(calc_freq_pnl(
            self.log["portfolio_value"], self.log["timestamp"], freq="7D")[-1]*100, label="1W_pnl_percentage"))

    def print(self):
        print("\n"*1)
        print("-"*50, "[BACKTEST RESULT]", "-"*50)
        for key, value in self.result.items():
            print(f"{key}:{round(value, 3)}")

    def export_result(self, path="./bt_result/", name="result.json"):
        if not os.path.exists(path):
            os.makedirs(path)
        print("saving result to: ", path + name)
        with open(path + name, "w") as f:
            f.write(json.dumps(self.result))

    def export_log(self, path="./bt_result/", name="log.csv"):
        if not os.path.exists(path):
            os.makedirs(path)
    
        df = pd.DataFrame()
        for key in PnlLogLabel.lst:
            try: df[key] = self.log[key]
            except: print(key)
        print("saving log: ", path + "broker_" + name)
        df.to_csv(path + "broker_" + name)
        
        df = pd.DataFrame()
        for key in PortFolioLogLabel.lst:
            df[key] = self.log[key]
        print("saving log: ", path + "portfolio_" + name)
        df.to_csv(path + "portfolio_" + name)

    def export(self, path="./bt_result/"):
        print("\n")
        print("-"*50, "[EXPORTING RESULT/LOG]", "-"*50)
        self.export_log(path)
        self.export_result(path)


