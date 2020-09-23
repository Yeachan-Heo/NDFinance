from ndfinance.brokers.backtest import *
from ndfinance.core import BacktestEngine
from ndfinance.analysis.backtest.analyzer import BacktestAnalyzer
from ndfinance.strategies.basic import SameWeightBuyHold
import matplotlib.pyplot as plt


def main(data_paths, tickers, **kwargs):
    dp = BacktestDataProvider()
    dp.add_ohlc_dataframes(dataframes_or_paths=data_paths, tickers=tickers)

    indexer = TimeIndexer(dp.get_shortest_timestamp_seq())
    dp.set_indexer(indexer)

    brk = BacktestBroker(WithDrawConfig(use=False), dp, initial_margin=10000)
    [brk.add_asset(Futures(ticker=ticker)) for ticker in tickers]

    strategy = SameWeightBuyHold()

    engine = BacktestEngine()
    engine.register_broker(brk)
    engine.register_strategy(strategy)

    log = engine.run()

    analyzer = BacktestAnalyzer(log)
    analyzer.print()

    plt.plot(log["portfolio_value"] / log["portfolio_value"][0])
    plt.show()

if __name__ == '__main__':
    main(
        [
         "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/ETHUSD.csv",
         "/home/bellmanlabs/Data/bitmex/trade/ohlc/1H/XBTUSD.csv"
        ],
        [
            "ETHUSD",
            "XBTUSD"
        ]
    )