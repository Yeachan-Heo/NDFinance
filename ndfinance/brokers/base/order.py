from ndfinance.brokers.base import *
from ndfinance.utils import get_random_string
from ndfinance.brokers.base.asset import Asset


class Order:
    def __init__(self, type, asset):
        self.type = type
        self.asset: Asset = asset
        self.ticker = self.asset.ticker
        self.id = get_random_string(20)

class OrderSide:
    sell = -1
    buy = 1

class OrderTypes():
    stop_loss = "stop_loss"
    take_profit = "take_profit"
    market = "market"
    limit = "limit"
    weight = "weight"
    close = "close"
    timecut_close = "timecut_close"
    rebalance = "rebalance"


class StopLoss(Order):
    def __init__(self, asset, threshold):
        super(StopLoss, self).__init__(OrderTypes.stop_loss, asset)
        self.threshold = -threshold


class TakeProfit(Order):
    def __init__(self, asset, threshold):
        super(TakeProfit, self).__init__(OrderTypes.take_profit, asset)
        self.type = OrderTypes.take_profit
        self.threshold = threshold


class Market(Order):
    def __init__(self, asset, amount, side):
        super(Market, self).__init__(OrderTypes.market, asset)
        self.amount = amount
        self.side = side

    def __str__(self):
        side = "buy" if self.side == OrderSide.buy else "sell"
        return f"type:{self.type},ticker:{self.ticker},amount:{self.amount},side:{self.side}"

class Limit(Order):
    def __init__(self, asset, amount, side, price):
        super(Limit, self).__init__(OrderTypes.limit, asset)
        self.side = side
        self.price = price
        self.amount = amount
    
    def __str__(self):
        side = "buy" if self.side == OrderSide.buy else "sell"
        return f"type:{self.type},ticker:{self.ticker},amount:{self.amount},side:{self.side},price:{self.price}"


class Close(Order):
    def __init__(self, asset, market=True, price=None):
        super(Close, self).__init__(OrderTypes.close, asset)
        self.market = market
        self.price = price

    def __str__(self):
        side = "buy" if self.side == OrderSide.buy else "sell"
        return f"type:{self.type},ticker:{self.ticker},market:{self.market},price:{self.price}"


class Weight(Order):
    def __init__(self, asset, value, side, weight=1, market=True, price=None):
        self.weight = weight
        self.value = value
        self.side = side
        self.weightvalue = self.weight * self.value
        self.market = market
        self.price = price
        if (not market) & (price is None):
            raise ValueError(
                "if you're placing an limit order by setting(market=False), you have to set up the limit price")
        super(Weight, self).__init__(OrderTypes.weight, asset)
    
    def __str__(self):
        side = "buy" if self.side == OrderSide.buy else "sell"
        return f"type:{self.type},ticker:{self.ticker},value:{self.value},weight:{self.weight},side:{self.side},market:{self.market},price:{self.price}"

    def get_amount(self, price):
        amount = (self.weightvalue / price) // \
                             self.asset.min_amount * self.asset.min_amount
        return amount

    def to_limit(self):
        return Limit(self.asset, self.get_amount(self.price), self.side, self.price)

    def to_market(self, market_price):
        return Market(self.asset, self.get_amount(market_price), self.side)


import datetime
from dateutils import relativedelta


class TimeCutClose(Order):
    def __init__(self, asset, timestamp, **delta_kwargs):
        super(TimeCutClose, self).__init__(type=OrderTypes.timecut_close, asset=asset)
        if isinstance(timestamp, datetime.datetime):
            self.timestamp = (timestamp + relativedelta(**delta_kwargs)).timestamp()
        else:
            self.timestamp = (datetime.datetime.fromtimestamp(timestamp)
                          + relativedelta(**delta_kwargs)).timestamp()

    def __str__(self):
        side = "buy" if self.side == OrderSide.buy else "sell"
        return f"type:{self.type},ticker:{self.ticker},timestamp:{self.timestamp}"

        
class Rebalance(Order):
    def __init__(self, tickers, weights, normalize=False):
        super(Rebalance, self).__init__(OrderTypes.rebalance, Asset("None"))
        self.tickers = tickers
        self.weights = weights

        if normalize:
            sum_weights = np.sum(np.abs(self.weights))
            self.weights = [x / sum_weights for x in self.weights]
        self.dict_ = dict(zip(self.assets, self.weights))

    def __getitem__(self, item):
        return self.dict_[item]


    def items(self):
        return self.dict_.items()


    def __str__(self):
        return "RebalanceOrder"
        