from ndfinance.brokers.backtest import *
from ndfinance.core import BacktestEngine
from ndfinance.analysis.backtest.analyzer import BacktestAnalyzer
from ndfinance.analysis.technical import RateOfChange
from ndfinance.visualizers.backtest_visualizer import BasicVisualizer
from ndfinance.strategies.trend import ActualMomentumStratagy
import matplotlib.pyplot as plt


def main(tickers, **kwargs):
    path="./bt_results/actualmomentum/"
    dp = BacktestDataProvider()
    dp.add_yf_tickers(*tickers)
    dp.add_technical_indicators(tickers, [TimeFrames.day], [RateOfChange(20)])

    indexer = TimeIndexer(dp.get_shortest_timestamp_seq())
    dp.set_indexer(indexer)

    brk = BacktestBroker(dp, initial_margin=10000)
    [brk.add_asset(Futures(ticker=ticker)) for ticker in tickers]

    strategy = ActualMomentumStratagy(
        momentum_threshold=1, 
        rebalance_period=TimeFrames.day*30,
        momentum_label="ROCR20",
    )

    engine = BacktestEngine()
    engine.register_broker(brk)
    engine.register_strategy(strategy)

    log = engine.run()
    
    analyzer = BacktestAnalyzer(log)
    analyzer.print()
    analyzer.export_log(path=path)
    analyzer.export_result(path=path)
    
    from pprint import pprint as print 

    visualizer = BasicVisualizer()
    visualizer.plot_log(log)

    visualizer.export_figures(path=path)

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