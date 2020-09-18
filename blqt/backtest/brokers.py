from blqt.backtest.base import *
from blqt.backtest.data_providers import *
from typing import *
import ray

class Broker(object):
    def __init__(self, *args, **kwargs):
        pass

    def order(self, ticker, amount, order_type):
        pass


class BackTestBroker(Broker):
    def __init__(self, data_provider, time_indexer,
                 use_withdraw=False, withdraw_period=TimeFrames.Minute*60000, *args, **kwargs):
        super(BackTestBroker, self).__init__(*args, **kwargs)
        self.margin = None
        self.tickers: Dict[str, FinancialProduct] = {}
        self.positions: Dict[str, Position] = {}
        self.indexer = time_indexer
        self.data_provider: BacktestDataProvider = data_provider
        self.trade_hist = []
        self.trade_hist_rate = []
        self.trade_hist_rate_weighted = []

        self.use_withdraw = use_withdraw
        self.withdraw_period = withdraw_period
        self.last_withdraw = self.indexer.timestamp

    def initialize(self, margin):
        self.initial_margin = margin
        self.margin = margin
        self.pv = margin
        self.withdraw_account = 0
        self.positions.clear()

    def withdraw(self, n):
        self.withdraw_account += n

    def deposit(self, money):
        self.margin += money

    def add_ticker(self, ticker: FinancialProduct):
        self.tickers[ticker.ticker] = ticker

    def calc_pv(self):
        self.pv = self.margin + self.withdraw_account
        unrealized = 0
        for key, item in self.positions.items():
            item.update_value(self.data_provider.current(key, "close") * (1 - item.product.slippage * np.sign(item.amount)))
            unrealized += item.unrealized_pnl
        pos_values = np.sum([np.abs(p.position_value) for p in self.positions.values()])

        self.pv += unrealized
        self.orderable_margin = self.margin - pos_values
        self.leverage = pos_values / self.pv

        if self.use_withdraw:
            if self.indexer.timestamp - self.last_withdraw >= self.withdraw_period:
                withdraw = self.margin - self.initial_margin
                self.withdraw(withdraw)
                self.deposit(-withdraw)
                self.last_withdraw = self.indexer.timestamp


    def update_weight(self):
        [item.update_weight(self.pv) for item in self.positions.values()]

    def order_limit(self, ticker, amount, price):
        ret = 0

        if (amount == 0) or (amount == np.nan):
            return ret

        price = price * (1 + self.tickers[ticker].slippage * np.sign(amount))

        if ticker in self.positions.keys():
            realized = self.positions[ticker].add(
                amount=amount, avg_price=price, timestamp=self.indexer.timestamp)
            self.deposit(realized)

            if np.abs(realized) > 0:
                ret = self.positions[ticker].unrealized_pnl_rate*self.positions[ticker].weight
                self.trade_hist_rate_weighted.append(ret)
                self.trade_hist_rate.append(self.positions[ticker].unrealized_pnl_rate)
                self.trade_hist.append(realized)

            if (self.positions[ticker].amount == 0) or (self.positions[ticker].amount == np.nan):
                del self.positions[ticker]
                self.calc_pv()
        else:
            self.positions[ticker] = Position(self.tickers[ticker], amount, price, self.indexer.timestamp)

        return ret


    def order_market(self, ticker, amount):
        price = self.data_provider.current(ticker, label="close")
        return self.order_limit(ticker, amount, price=price)

    def order_target_weight(self, value, ticker, weight, price=None):

        product = self.tickers[ticker]
        min_amount = product.min_amount

        if price is None:
            price = self.data_provider.current(ticker, label="close")

        target_amount = value * weight / price // min_amount * min_amount



        amount = target_amount - self.positions[ticker].amount if ticker in self.positions.keys() else target_amount
        return self.order_limit(ticker, amount, price)

    def order_target_weight_pv(self, ticker, weight, price=None):
        return self.order_target_weight(self.pv, ticker, weight, price)

    def order_target_weight_margin(self, ticker, weight, price=None):
        self.calc_pv()
        return self.order_target_weight(self.orderable_margin, ticker, weight, price)

    def close_position(self, ticker, price=None):
        if price is None:
            return self.order_market(ticker, -self.positions[ticker].amount)
        return self.order_limit(ticker, -self.positions[ticker].amount, price)


from webull import paper_webull, webull


class WebullBroker(Broker):
    def __init__(self, paper=True, id=None, pw=None):
        super(WebullBroker, self).__init__()
        self.webull = paper_webull() if paper else webull()

        if (id is None) or (pw is None):
            id, pw = self.request_login_info()

        self.webull.login(username=id, password=pw)

    def get_pv(self):
        portfoilo = self.webull.get_portfolio()
        self._market_value = portfoilo["totalMarketValue"]
        self._cash = portfoilo["usableCash"]
        pv = self._market_value + self._cash
        self._pv = pv
        return pv

    @property
    def pv(self):
        return self.get_pv()

    def request_login_info(self):
        id = input("your id: ")
        pw = input("your password: ")
        return id, pw

    def order_limit(self, ticker, amount, price):
        side = "BUY" if amount > 0 else "SELL"
        self.webull.place_order(stock=ticker, price=price, action=side, quant=abs(amount))

    def order_market(self, ticker, amount):
        side = "BUY" if amount > 0 else "SELL"
        self.webull.place_order(stock=ticker, action=side, quant=abs(amount), orderType="MKT")

    def order_target_weight(self, value, ticker, weight, price=None):
        side = np.sign(weight)

        price_was_none = price is None

        if price is None:
            price = float(self.webull.get_quote(stock=ticker)["pPrice"])

        order_size = np.clip(np.abs(value * weight), 0, self._cash)

        amount = order_size // price * side

        self.order_limit(ticker, amount, price) if price_was_none else self.order_market(ticker, amount)

    def order_target_weight_pv(self, ticker, weight, price):
        self.order_target_weight(self.pv, ticker, weight, price)

    def order_target_weight_margin(self, ticker, weight, price):
        self.get_pv()
        self.order_target_weight(self._cash, ticker, weight, price)

import ccxt

class BinanceFuturesBroker(Broker):
    def __init__(self, api_key, secret, margin_currency="USDT"):
        super(BinanceFuturesBroker, self).__init__()
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'timeout': 30000,
            'enableRateLimit': True,
            'futures' : True
        })
        self.margin_currency = margin_currency

        print(self.exchange.id, self.exchange.load_markets())

    def order_market(self, ticker, amount):
        side = sign(amount)

        if side == 0:
            return

        amount = abs(amount)

        if side == 1:
            self.exchange.create_market_buy_order(
                symbol=ticker,
                amount=amount
            )
        elif side == -1:
            self.exchange.create_market_sell_order(
                symbol=ticker,
                amount=amount
            )

    def order_limit(self, ticker, amount, price):
        side = sign(amount)

        if side == 0:
            return

        amount = abs(amount)

        if side == 1:
            self.exchange.create_order(
                symbol=ticker,
                type="limit",
                side="buy",
                amount=amount,
                price=price,
            )
        elif side == -1:
            self.exchange.create_order(
                symbol=ticker,
                type="limit",
                side="sell",
                amount=amount,
                price=price,
            )

    def order_target_weight(self, value, ticker, weight, price=None):

        product = self.tickers[ticker]
        min_amount = product.min_amount

        target_amount = value * weight / (
                price // product.tick_size * product.tick_value
        ) // min_amount * min_amount

        amount = target_amount - self.positions[ticker].amount if ticker in self.positions.keys() else target_amount

        if price is None:
            self.order_market(ticker, amount)
        else:
            self.order_limit(ticker, amount, price)


    def order_target_weight_margin(self, ticker):
        currency = ticker.split("/")[-1]
        free = 0
        for asset_dict in self.exchange.fetch_balance()["assets"]:
            if asset_dict["asset"] == currency:
                free = 1









