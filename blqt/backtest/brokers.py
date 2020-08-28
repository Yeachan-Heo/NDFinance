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
    def __init__(self, data_provider, time_indexer, *args, **kwargs):
        super(BackTestBroker, self).__init__(*args, **kwargs)
        self.margin = None
        self.tickers: Dict[str, FinancialProduct] = {}
        self.positions: Dict[str, Position] = {}
        self.indexer = time_indexer
        self.data_provider: BacktestDataProvider = data_provider
        self.trade_hist = []
        self.trade_hist_rate = []

    def initialize(self, margin):
        self.margin = margin
        self.pv = margin
        self.positions.clear()

    def deposit(self, money):
        self.margin += money

    def add_ticker(self, ticker: FinancialProduct):
        self.tickers[ticker.ticker] = ticker

    def calc_pv(self):
        self.pv = self.margin
        for key, item in self.positions.items():
            item.update_value(self.data_provider.current(key, "close") * (1 - item.product.slippage * np.sign(item.amount)))
            self.pv += item.unrealized_pnl
        pos_values = np.sum([p.position_value for p in self.positions.values()])

        self.orderable_margin = self.pv - pos_values
        self.leverage = pos_values / self.pv

    def update_weight(self):
        [item.update_weight(self.pv) for item in self.positions.values()]

    def order_limit(self, ticker, amount, price):
        if amount == 0:
            return
        price = price * (1 + self.tickers[ticker].slippage * np.sign(amount))
        if ticker in self.positions.keys():
            realized = self.positions[ticker].add(
                amount=amount, avg_price=price, timestamp=self.indexer.timestamp)
            self.deposit(realized)

            if np.abs(realized) > 0:
                self.trade_hist_rate.append(
                    self.positions[ticker].unrealized_pnl_rate*self.positions[ticker].weight
                )
                self.trade_hist.append(realized)

            if self.positions[ticker].amount == 0:
                del self.positions[ticker]
                self.calc_pv()
        else:
            self.positions[ticker] = Position(self.tickers[ticker], amount, price, self.indexer.timestamp)

    def order_market(self, ticker, amount):
        price = self.data_provider.current(ticker, label="close")
        self.order_limit(ticker, amount, price=price)

    def order_target_weight(self, value, ticker, weight, price=None):

        product = self.tickers[ticker]
        min_amount = product.min_amount

        if price is None:
            price = self.data_provider.current(ticker, label="close")

        target_amount = value * weight / (
                price // product.tick_size * product.tick_value
        ) // min_amount * min_amount

        amount = target_amount - self.positions[ticker].amount if ticker in self.positions.keys() else target_amount
        self.order_limit(ticker, amount, price)

    def order_target_weight_pv(self, ticker, weight, price=None):
        self.order_target_weight(self.pv, ticker, weight, price)

    def order_target_weight_margin(self, ticker, weight, price=None):
        self.order_target_weight(self.orderable_margin, ticker, weight, price)

    def close_position(self, ticker, price=None):
        if price is None:
            self.order_market(ticker, -self.positions[ticker].amount)
            return
        self.order_limit(ticker, -self.positions[ticker].amount, price)


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


