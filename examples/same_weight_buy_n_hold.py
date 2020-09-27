from ndfinance.brokers.backtest import *
from ndfinance.core import BacktestEngine
from ndfinance.analysis.backtest.analyzer import BacktestAnalyzer
from ndfinance.analysis.technical import RateOfChange
from ndfinance.visualizers.backtest_visualizer import BasicVisualizer
from ndfinance.strategies.basic import SameWeightBuyHold
import matplotlib.pyplot as plt


def main(tickers, **kwargs):
    path="./bt_results/same_weight_bnh/"
    dp = BacktestDataProvider()
    dp.add_yf_tickers(*tickers)
    dp.add_technical_indicators(tickers, [TimeFrames.day], [RateOfChange(20)])

    indexer = TimeIndexer(dp.get_shortest_timestamp_seq())
    dp.set_indexer(indexer)

    brk = BacktestBroker(dp, initial_margin=10000)
    [brk.add_asset(Asset(ticker=ticker)) for ticker in tickers]

    strategy = SameWeightBuyHold()

    engine = BacktestEngine()
    engine.register_broker(brk)
    engine.register_strategy(strategy)

    log = engine.run()
    
    analyzer = BacktestAnalyzer(log)
    analyzer.print()
    analyzer.export(path)

    visualizer = BasicVisualizer()
    visualizer.plot_log(log)

    visualizer.export(path=path)

if __name__ == '__main__':
    main(
        [
            "AAPL",
            "FB",
            "NFLX",
            "GOOGL",
            "NVDA",
            "TSLA",
            "AMZN",
            "TWTR",
            "BIDU",
            "BABA"
        ]
    )