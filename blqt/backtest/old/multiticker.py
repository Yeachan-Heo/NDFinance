from datetime import datetime, timedelta
import numpy as np
from typing import *
import pandas as pd
import matplotlib.pyplot as plt
import threading

import talib.abstract as ta

from collections import deque
from copy import deepcopy
from dateutils import relativedelta

class FundamentalData:
    def __init__(self, data, time_col):
        self.data = data
        self.timestamp = None
        self.time_col = time_col

    def set_timestamp(self, ts):
        self.timestamp = ts

    def update_data(self):
        self.current_data = (self.data.loc[self.data[self.time_col] < self.timestamp])

    def __getitem__(self, item):
        return self.current_data[item]


class TickData:
    def __init__(self, data, time_col, price_col):
        self.data = data
        self.timestamp = None
        self.price_data = data[price_col].to_numpy()
        self.time_data = data[time_col]

    def set_timestamp(self, ts):
        self.timestamp = ts

    def update_price(self):
        idx = len(self.time_data.loc[self.time_data < self.timestamp])
        self.price = self.price_data[idx]


class OHLCVData:
    def __init__(self, data):
        self.data = data

    def set_timestamp(self, ts):
        self.timestamp = ts

    def update_price(self):
        self.current_data = self.data.loc[self.data["TimeStamp"] < self.timestamp].iloc[-1]

    def add_ta(self, name, value):
        self.data[name] = value

    def __getitem__(self, item):
        return self.current_data[item]


class PriceData:
    def __init__(self,
                 tick_data: Optional[TickData],
                 ohlcv_data : OHLCVData
                 ):

        self.tick_data = tick_data
        self.ohlcv_data = ohlcv_data

    def update_data(self):
        if self.tick_data:
            self.tick_data.update_price()
        if self.ohlcv_data:
            self.ohlcv_data.update_price()
        self.update_current_price()

    def update_current_price(self):
        if self.tick_data:
            self.price = self.tick_data.price
        elif self.ohlcv_data:
            self.price = self.ohlcv_data["Close"]

    def set_timestamp(self, ts):
        self.timestamp = ts
        if self.tick_data:
            self.tick_data.set_timestamp(self.timestamp)
        if self.ohlcv_data:
            self.ohlcv_data.set_timestamp(self.timestamp)


class FinancialProduct:
    def __init__(self, ticker, fee, tick, tick_value, slippage, min_amount,
                 price_data: PriceData, fundamental_data: FundamentalData,
                 margin_requirement, margin_requirement_maintain,
                 ):
        
        self.ticker = ticker
        
        self.fundamental_data = fundamental_data
        self.price_data = price_data

        self.tick_value = tick_value

        self.mr = margin_requirement
        self.mrm = margin_requirement_maintain

        self.slippage = slippage
        self.tick = tick
        self.fee = fee

        self.min_amount = min_amount

    def set_timestamp(self, ts):
        if self.fundamental_data:
            self.fundamental_data.set_timestamp(ts)
        self.price_data.set_timestamp(ts)

    def update_data(self):
        self.price_data.update_data()
        if self.fundamental_data:
            self.fundamental_data.update_data()
        self.price = self.price_data.price
        self.value = self.price / self.tick * self.tick_value
        self.bid_price = (self.price + self.tick * self.slippage) * (1+self.fee)
        self.ask_price = (self.price - self.tick * self.slippage) * (1-self.fee)


class Position:
    def __init__(self, product: FinancialProduct, amount, avg_price=None):
        self.amount = amount
        self.bidorask = np.sign(amount)
        self.product = product
        self.avg_price = avg_price
        if self.avg_price is None:
            self.avg_price = (self.product.bid_price if self.bidorask == 1 else self.product.ask_price)
        self.init_pos_value()
        self.update_value()
    
    def init_pos_value(self):
        self.first_pos_value = self.avg_price * self.amount

    def update_value(self):
        self.product.update_data()
        self.pos_value = (self.product.bid_price if self.bidorask == -1 else self.product.ask_price) * self.amount
        self.pal = self.pos_value - self.first_pos_value
        self.pal_perc = (self.pos_value / self.first_pos_value - 1) * self.bidorask

    def add(self, pos):
        sign_is_same = np.sign(pos.amount) == np.sign(self.amount)
        n = self.amount + pos.amount
        if self.amount == 0:
            return 0, pos
        if sign_is_same:
            avg_price = (self.amount * self.avg_price + pos.amount * pos.avg_price) / n
            new_pos = Position(self.product, n, avg_price)
            return 0, new_pos
        if not sign_is_same:
            realized_pal = self.pal * np.clip(np.abs(pos.amount / self.amount), a_max=1, a_min=0)
            avg_price = pos.avg_price if np.abs(pos.amount) > np.abs(self.amount) else self.avg_price
            new_pos = Position(self.product, n, avg_price)
            return realized_pal, new_pos
        raise ValueError


class Account:
    def __init__(self, margin):
        self.positions = {}
        self.margin = margin
        self.pv = margin

    def deposit(self, amount):
        self.margin += amount

    def add_position(self, position):
        if position.product.ticker in self.positions.keys():
            realized_pal, new_pos = self.positions[position.product.ticker].add(position)
            self.positions[position.product.ticker] = new_pos
            self.deposit(realized_pal)
        else:
            self.positions[position.product.ticker] = position

    def update_pv(self):
        for value in self.positions.values():
            value.update_value()
        self.pv = self.margin + np.sum([v.pal for v in self.positions.values()]) if self.positions else self.pv

    def __str__(self):
        ret = f"""
        pv:{self.pv}, margin:{self.margin}
        [Position]
        """
        for key, value in self.positions.items():
            ret += f"[{key}], amount:{value.amount}, p&l(%):{np.round(value.pal_perc*100,2)}%"
        return ret


class Market:
    def __init__(self, account:Account):
        self.tickers: Dict[str, FinancialProduct] = {}
        self.account = account
        self.timestamp = None

        self.first_timestamp = None
        self.last_timestamp = None

    def IPO(self, product:FinancialProduct):
        self.tickers[product.ticker] = product

        if not self.first_timestamp:
            self.first_timestamp = self.tickers[product.ticker].price_data.ohlcv_data.data["TimeStamp"].iloc[0]
            self.last_timestamp = self.tickers[product.ticker].price_data.ohlcv_data.data["TimeStamp"].iloc[-1]
            self.timestamp = self.first_timestamp

        elif self.first_timestamp:
            first_ts = self.tickers[product.ticker].price_data.ohlcv_data.data["TimeStamp"].iloc[0]
            last_ts = self.tickers[product.ticker].price_data.ohlcv_data.data["TimeStamp"].iloc[-1]

            if self.first_timestamp < first_ts:
                self.first_timestamp = first_ts

            if self.last_timestamp > last_ts:
                self.last_timestamp = last_ts

    def set_timestamp(self, *args, **kwargs):
        for key, value in self.tickers.items():
            value.set_timestamp(self.timestamp)

    def update_timestamp(self, *args, **kwargs):
        self.timestamp += relativedelta(*args, **kwargs)
        self.set_timestamp()
        for value in self.tickers.values():
            value.update_data()
        self.account.update_pv()

    def get_max_order(self, ticker, price):
        if not ticker in self.tickers.keys():
            raise ValueError
        max_order_amount = (self.account.pv / (price * self.tickers[ticker].mr)) // self.tickers[ticker].min_amount * self.tickers[ticker].min_amount
        return max_order_amount

    def order_limit(self, ticker, price, amount):

        if not ticker in self.tickers.keys():
            raise ValueError

        direction = np.sign(amount)

        amount = np.clip(np.abs(amount), 0, self.get_max_order(ticker, price))

        if amount < self.tickers[ticker].min_amount:
            return

        amount = amount * direction

        self.account.add_position(
            Position(self.tickers[ticker], amount=amount, avg_price=price))

    def order_market(self, ticker, amount):
        amount = amount // self.tickers[ticker].min_amount * self.tickers[ticker].min_amount
        self.order_limit(
            ticker, self.tickers[ticker].bid_price if amount > 0 else self.tickers[ticker].ask_price, amount)

    def order_weight(self, ticker, weight):
        if ticker in self.account.positions.keys():
            current_weight = self.account.positions[ticker].pos_value / self.account.pv
        else:
            current_weight = 0
        order_money = self.account.pv * (weight - current_weight)
        order_amount = order_money / (self.tickers[ticker].bid_price if weight > 0 else self.tickers[ticker].ask_price)
        self.order_market(ticker, order_amount)

    def order_clear(self, ticker):
        if not ticker in self.tickers.keys():
            raise ValueError
        self.order_market(ticker, -self.account.positions[ticker].amount)

    def isdone(self):
        return self.timestamp >= self.last_timestamp


class Renderer:
    def __init__(self):
        super(Renderer, self).__init__()
        self.data = {}
        plt.ion()

    def put_data(self, name, value):
        if name in self.data.keys():
            self.data[name].append(value)
        else:
            self.data[name] = [value]

    def render(self, title="Renderer", render_n=None):
        plt.clf()
        plt.title(title)
        for key, value in self.data.items():
            plt.plot(np.array(value if not render_n else value[-render_n:]), label=key)
        plt.legend()
        plt.draw()
        plt.pause(1e-20)

if __name__ == '__main__':
    df = pd.read_csv("../../../data/NQ_2017_2020.csv")
    df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])
    data = OHLCVData(df)

    data.add_ta("aroon", ta.AROONOSC(data.data["High"], data.data["Low"], timeperiod=3000))
    data.add_ta("mom", ta.MOM(data.data["Close"], timeperiod=5000))
    data.add_ta("MA20", ta.SMA(data.data["Close"], timeperiod=10000))

    data = PriceData(None, data)
    product = FinancialProduct("NDXF", 0.000015, 0.25, 1, 0, 1, data, None, 0.01, 0.009)
    account = Account(100000)

    market = Market(account)

    market.IPO(product)
    market.update_timestamp(days=7)
    renderer = Renderer()

    first_price = product.price_data.ohlcv_data["Close"]

    prev_pv = account.pv
    i = 0

    prev_ma = market.tickers["NDXF"].price_data.ohlcv_data["Close"]

    market.order_weight("NDXF", 1)

    while True:
        market.update_timestamp(days=1)
        renderer.put_data("pv", account.pv/100000)
        renderer.put_data("benchmark", product.price_data.ohlcv_data["Close"]/first_price)
        #renderer.render(title=str(account), render_n=1000)
        i += 1

        ma = market.tickers["NDXF"].price_data.ohlcv_data["MA20"] / market.tickers["NDXF"].price_data.ohlcv_data["Close"] - 1
        aroon = market.tickers["NDXF"].price_data.ohlcv_data["aroon"]

        if market.isdone():
            break

    print(account)
    renderer.render()
    plt.pause(100)










