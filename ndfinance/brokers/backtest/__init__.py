import ray
import warnings
from typing import *

from ndfinance.brokers.backtest.data_provider import BacktestDataProvider
from ndfinance.brokers.base import *
from ndfinance.utils.array_utils import LabeledScalarStorage, StructureDataset
from ndfinance.brokers.base.order import *

class PortFolioLogLabel:
    portfolio_value = "portfolio_value"
    portfolio_value_total = "portfolio_value_total"

    leverage = "leverage"
    leverage_total = "leverage_total"

    cash_weight_percentage = "cash_weight_percentage"
    cash_weight_percentage_total = "cash_weight_percentage_total"

    unrealized_pnl_percentage = "unrealized_pnl_percentage"
    unrealized_pnl_percentage_total = "unrealized_pnl_percentage_total"

    lst = [portfolio_value_total, portfolio_value,
            leverage, leverage_total,
            cash_weight_percentage, cash_weight_percentage_total,
            unrealized_pnl_percentage, unrealized_pnl_percentage_total,
            OHLCVT.timestamp]


class BacktestPortfolio:
    def __init__(self, initial_margin, withdraw_config: WithDrawConfig, data_provider):
        super(BacktestPortfolio, self).__init__()
        self.positions: Dict[str, Position] = {}

        self.withdraw_config = withdraw_config
        self.data_provider = data_provider
        self.indexer = self.data_provider.indexer
        self.initial_margin = initial_margin
        self.margin_account = initial_margin
        self.portfolio_value = initial_margin
        self.usable_margin = initial_margin
        self.withdraw_account = 0
        self.last_withdraw = self.indexer.timestamp

        self.log = LabeledScalarStorage(*PortFolioLogLabel.lst)

    def add_position(self, position: Position):
        if position.asset.ticker in self.positions.keys():
            realized = self.positions[position.asset.ticker].add_position(position)
            pnl_percentage = self.positions[position.asset.ticker].unrealized_pnl_percentage
            if self.positions[position.asset.ticker].amount == 0:
                del self.positions[position.asset.ticker]
        else:
            realized = 0
            pnl_percentage = 0
            self.positions[position.asset.ticker] = position
        return realized, pnl_percentage

    def write_log(self):
        self.log.add_scalar(PortFolioLogLabel.portfolio_value, self.portfolio_value)
        self.log.add_scalar(PortFolioLogLabel.portfolio_value_total, self.portfolio_value_total)

        self.log.add_scalar(PortFolioLogLabel.leverage, self.leverage)
        self.log.add_scalar(PortFolioLogLabel.leverage_total, self.leverage_total)

        self.log.add_scalar(PortFolioLogLabel.cash_weight_percentage, self.cash_weight_percentage)
        self.log.add_scalar(PortFolioLogLabel.cash_weight_percentage_total, self.cash_weight_percentage_total)

        self.log.add_scalar(PortFolioLogLabel.unrealized_pnl_percentage, self.unrealized_pnl_percentage)
        self.log.add_scalar(PortFolioLogLabel.unrealized_pnl_percentage_total, self.unrealized_pnl_percentage_total)

        self.log.add_scalar(OHLCVT.timestamp, self.indexer.timestamp)

    def update_portfolio_value(self):
        self.unrealized_pnl = 0
        self.position_margin = 0
        self.position_value = 0

        for ticker, position in self.positions.items():
            position.evaluate(self.data_provider.current_price(ticker))
            self.unrealized_pnl += position.unrealized_pnl
            self.position_margin += position.position_margin
            self.position_value += position.position_value

        self.portfolio_value = self.margin_account + self.unrealized_pnl
        self.portfolio_value_total = self.portfolio_value + self.withdraw_account
        self.usable_margin = self.margin_account - self.position_margin

        self.leverage = self.position_value / self.portfolio_value
        self.leverage_total = self.position_value / self.portfolio_value_total

        self.cash_weight_percentage = (1 - self.leverage) * 100
        self.cash_weight_percentage_total = (1 - self.leverage_total) * 100

        self.unrealized_pnl_percentage = self.unrealized_pnl / self.portfolio_value * 100
        self.unrealized_pnl_percentage_total = self.unrealized_pnl / self.portfolio_value_total * 100

        [position.evaluate_weight(
            self.portfolio_value, self.portfolio_value_total, self.position_value)
            for position in self.positions.values()]

        self.write_log()

    def deposit_margin(self, amount):
        self.margin_account += amount

    def deposit_withdraw(self, amount):
        self.margin_account -= amount
        self.withdraw_account += amount

    def withdraw(self):
        if not self.withdraw_config.use: return
        if self.indexer.timestamp - self.last_withdraw > self.withdraw_config._period:
            if self.withdraw_config.mode == WithDrawTypes.percentage:
                self.deposit_withdraw(self.portfolio_value * self.withdraw_config._percentage)
                return
            if self.withdraw_config.mode == WithDrawTypes.constant:
                self.deposit_withdraw(self.withdraw_config._amount)
                return
            if self.withdraw_config.mode == WithDrawTypes.initial_margin:
                self.deposit_withdraw(self.portfolio_value - self.initial_margin)
                return

    def get_log(self):
        return self.log


class PnlLogLabel:
    realized_pnl = "realized_pnl"
    realized_pnl_percentage = "realized_pnl_percentage"
    realized_pnl_percentage_weighted = "realized_pnl_percentage_weighted"
    order_timestamp = "order_timestamp"
    order_type = "order"

    lst = [realized_pnl,
           realized_pnl_percentage,
           realized_pnl_percentage_weighted,
           order_timestamp,
           order_type]


class BacktestBroker(Broker):
    def __init__(self,
                 data_provider: BacktestDataProvider,
                 withdraw_config: WithDrawConfig = WithDrawConfig(use=False),
                 initial_margin: float = 1e+7):

        super(BacktestBroker, self).__init__(data_provider, withdraw_config)
        # initialize accounts
        self.portfolio = BacktestPortfolio(initial_margin, withdraw_config, data_provider)
        self.assets: Dict[str, Asset] = {}
        self.order_queue = {}
        self.data_provider: BacktestDataProvider
        self.log = LabeledScalarStorage(*PnlLogLabel.lst)

    def reset(self):
        return self.__init__(
            self.data_provider, self.portfolio.withdraw_config, self.portfolio.initial_margin)

    def add_asset(self, *args):
        for arg in args:
            self.assets[arg.ticker] = arg

    def add_order_to_queue(self, order):
        self.order_queue[order.id] = order

    def run_queue(self):
        [self.order(o, from_queue=True) for o in list(self.order_queue.values())]

    def _order_limit_force(self, order: Limit, market=False):
        if (order.amount == np.nan) or (order.amount == 0):
            warnings.warn(f"invalid value: {order.amount} encountered in limit order. ignoring the order")
            return

        order.price = (1 + order.side * order.asset.fee) * order.price

        if market:
            order.price = (1 + order.side * order.asset.slippage) * order.price

        order.amount = np.clip(order.amount, 0, (self.portfolio.usable_margin / (order.price * order.asset.margin_percentage)) // order.asset.min_amount * order.asset.min_amount)

        new_position = Position(
            order.asset, order.price, order.amount, order.side, self.indexer.timestamp)

        realized, pnl_percentage = self.portfolio.add_position(new_position)
        if not realized: pnl_percentage : 0
        realized_pnl_percentage_weighted = realized / self.portfolio.portfolio_value * 100

        self.log.add_scalar(PnlLogLabel.realized_pnl, realized)
        self.log.add_scalar(PnlLogLabel.realized_pnl_percentage, pnl_percentage)
        self.log.add_scalar(PnlLogLabel.realized_pnl_percentage_weighted, realized_pnl_percentage_weighted)


        return realized

    def _order_limit(self, order: Limit, from_queue=False):
        if from_queue:
            if order.side == OrderSide.sell:
                if order.price <= self.data_provider.current_ohlc(
                        order.asset.ticker, label=OHLCVT.high):
                    ret = self._order_limit_force(order)
                    del self.order_queue[order.id]
                    return ret
                return 0
            elif order.side == OrderSide.buy:
                if order.price >= self.data_provider.current_ohlc(
                        order.asset.ticker, label=OHLCVT.low):
                    ret = self._order_limit_force(order)
                    del self.order_queue[order.id]
                    return ret
                return 0
            else:
                raise ValueError(f"invalid order side: {order.side}")
        else:
            if order.side == OrderSide.sell:
                if order.price <= self.data_provider.current_price(
                        order.asset.ticker):
                    return self._order_limit_force(order)
                self.add_order_to_queue(order)
                return 0
            elif order.side == OrderSide.buy:
                if order.price >= self.data_provider.current_price(
                        order.asset.ticker):
                    return self._order_limit_force(order)
                self.add_order_to_queue(order)
                return 0
            else:
                raise ValueError(f"invalid order side: {order.side}")

    def _order_market(self, order: Market):
        return self._order_limit_force(
            Limit(order.asset, order.amount, order.side,
                  self.data_provider.current_price(order.asset.ticker)), market=True)

    def _order_weight(self, order: Weight):
        if order.market:
            order = order.to_market(self.data_provider.current_price(order.asset.ticker))
        else: order = order.to_limit()

        if order.asset.ticker in self.portfolio.positions.keys():
            position = self.portfolio.positions[order.asset.ticker]
            current_amount = position.amount * position.side
        else: current_amount = 0
        
        target_amount = order.amount * order.side

        amount = (target_amount - current_amount)
        amount, side = np.abs(amount), np.sign(amount)

        order.amount = amount
        order.side = side

        return self._order(order)

    def _order_close(self, order: Close):
        if not order.asset.ticker in self.portfolio.positions.keys():
            warnings.warn("attempted close order when there's no such position")
            return 0

        if order.market:
            return self._order_market(
                Market(order.asset, self.portfolio.positions[order.asset.ticker].amount,
                       -self.portfolio.positions[order.asset.ticker].side)
            )

        return self._order_limit(
            Limit(order.asset, self.portfolio.positions[order.asset.ticker].amount,
                  -self.portfolio.positions[order.asset.ticker].side, order.price)
        )

    def _order_stop_loss(self, order: StopLoss, from_queue):
        if self.portfolio.positions[order.asset.ticker].unrealized_pnl_percentage <= order.threshold:
            close_order = Close(order.asset)
            if from_queue:
                del self.order_queue[order.id]
            return self._order_close(close_order)
        if not from_queue:
            self.add_order_to_queue(order)
            return 0
        return 0

    def _order_take_profit(self, order: TakeProfit, from_queue):
        if self.portfolio.positions[order.asset.ticker].unrealized_pnl_percentage >= order.threshold:
            close_order = Close(order.asset)
            if from_queue:
                del self.order_queue[order.id]
            return self._order_close(close_order)
        if not from_queue:
            self.add_order_to_queue(order)
            return 0
        return 0

    def _order_timecut_close(self, order: TimeCutClose, from_queue):
        if self.indexer.timestamp >= order.timestamp:
            close_order = Close(order.asset)
            if from_queue:
                del self.order_queue[order.id]
            return self._order_close(close_order)
        if not from_queue:
            self.add_order_to_queue(order)
            return 0
        return 0

    def _order_rebalance(self, order: Rebalance):
        print(order.tickers)
        [
            self._order_close(Close(asset=self.assets[ticker])) 
            for ticker in self.portfolio.positions.keys() 
            if not ticker in order.tickers
        ]

        delta_weight_dict = {
            ticker:abs(self.portfolio.positions[ticker].weight-order[ticker])
            for ticker in self.portfolio.positions.keys()
            if ticker in order.tickers
        }

        [
            self._order_weight(Weight(
                    asset=self.assets[ticker], 
                    value=self.portfolio.portfolio_value, 
                    weight=np.abs(order[ticker]),
                    side=np.sign(order[ticker]
                ))) 
            for ticker in self.portfolio.positions.keys()
            if ticker in order.tickers
        ]
        
        [
            self._order_weight(Weight(
                    asset=self.assets[ticker], 
                    value=self.portfolio.portfolio_value, 
                    weight=np.abs(order[ticker]),
                    side=np.sign(order[ticker]
                ))) 
            for ticker, weight in order.items()
            if not ticker in self.portfolio.positions.keys()
        ]
        

    def _order(self, order, from_queue=False):
        if order.type == OrderTypes.limit:
            return self._order_limit(order, from_queue)
        if order.type == OrderTypes.close:
            return self._order_close(order)
        if order.type == OrderTypes.market:
            return self._order_market(order)
        if order.type == OrderTypes.weight:
            return self._order_weight(order)
        if order.type == OrderTypes.stop_loss:
            return self._order_stop_loss(order, from_queue)
        if order.type == OrderTypes.timecut_close:
            return self._order_timecut_close(order, from_queue)
        if order.type == OrderTypes.rebalance:
            return self._order_rebalance(order)
        raise ValueError(f"unregistered order type detected:{order.type}")

    def order(self, order, from_queue=False):
        realized = self._order(order, from_queue)
        if not realized is None:
            self.portfolio.deposit_margin(realized)
            self.log.add_scalar(PnlLogLabel.order_type, str(order))
            self.log.add_scalar(PnlLogLabel.order_timestamp, self.indexer.timestamp)

    def get_log(self):
        return self.portfolio.log + self.log

    def cancel_order(self, order_id=None, all=False):
        if all: self.order_queue = {}; return
        if isinstance(order_id, Order):
            order_id = order_id.id
        del self.order_queue[order_id]


