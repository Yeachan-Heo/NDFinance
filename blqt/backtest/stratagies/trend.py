from blqt.backtest.stratagies import *
from blqt.backtest.stratagies import Stratagy, TimeFrames


class ActualMomentumStratagy(Stratagy):
    def __init__(self, rebalance_period=60*60*24*14, benchmark_ticker="^KS11", leverage=1):
        super(ActualMomentumStratagy, self).__init__()
        self.broker : BackTestBroker
        self.last_rebalanced = -np.inf
        self.rebalance_period = rebalance_period
        self.benchmark_ticker = benchmark_ticker
        self.leverage = leverage

    def logic(self):
        if (self.broker.indexer.timestamp - self.last_rebalanced) > self.rebalance_period:
            momentum_lst = []
            for ticker in self.broker.tickers.keys():
                if ticker == self.benchmark_ticker:
                    momentum_lst.append(-1)
                    continue
                momentum = self.data_provider.current(ticker, "momentum")
                momentum_lst.append(momentum)

            weight = np.sum(list(filter(lambda x: x > 0, momentum_lst)))

            for ticker, momentum in zip(self.broker.tickers.keys(), momentum_lst):
                if momentum > 0:
                    self.broker.order_target_weight_pv(ticker, momentum/weight*self.leverage)
                else:
                    if ticker in self.broker.positions.keys():
                        self.broker.close_position(ticker)

            self.last_rebalanced = self.broker.indexer.timestamp


class ActualMomentumStratagyLongShort(Stratagy):
    def __init__(self, rebalance_period=60*60*24, benchmark_ticker="^KS11", leverage=1):
        super(ActualMomentumStratagyLongShort, self).__init__()
        self.broker : BackTestBroker
        self.last_rebalanced = -np.inf
        self.rebalance_period = rebalance_period
        self.benchmark_ticker = benchmark_ticker
        self.leverage = leverage

    def logic(self):
        if (self.broker.indexer.timestamp - self.last_rebalanced) > self.rebalance_period:
            momentum_lst = []
            for ticker in self.broker.tickers.keys():
                if ticker == self.benchmark_ticker:
                    momentum_lst.append(-1)
                    continue
                momentum = self.data_provider.current(ticker, "momentum")
                momentum_lst.append(momentum)



            for ticker, momentum in zip(self.broker.tickers.keys(), momentum_lst):
                if momentum > 0:
                    self.broker.order_market(ticker, self.leverage)
                elif momentum < 0:
                    self.broker.order_market(ticker, -self.leverage)

            self.last_rebalanced = self.broker.indexer.timestamp
