from ndfinance.brokers.backtest import *
from ndfinance.core import DistributedBacktestEngine
from ndfinance.analysis.backtest.analyzer import BacktestAnalyzer
from ndfinance.analysis.technical import RateOfChange
from ndfinance.visualizers.backtest_visualizer import BasicVisualizer
from ndfinance.strategies.trend import ActualMomentumStratagy
from ndfinance.callbacks import PositionWeightPrinterCallback
import matplotlib.pyplot as plt


def main(tickers, paths=None, n=1000, **kwargs):
    path="./bt_results/distributed_actualmomentum/"
    dp = BacktestDataProvider()
    if paths is None:
        dp.add_yf_tickers(*tickers)
    else:
        dp.add_ohlc_dataframes(paths, tickers)
    dp.add_technical_indicators(tickers, [TimeFrames.day], [RateOfChange(n)])

    indexer = TimeIndexer(dp.get_shortest_timestamp_seq())
    dp.set_indexer(indexer)
    dp.cut_data()

    brk = BacktestBroker(dp, initial_margin=10000)
    [brk.add_asset(Asset(ticker=ticker)) for ticker in tickers]

    strategy = ActualMomentumStratagy(
        momentum_threshold=1, 
        rebalance_period=TimeFrames.hour,
        momentum_label=f"ROCR{n}",
    )

    engine = DistributedBacktestEngine(n_cores=11)
    engine.register_broker(brk)
    engine.register_strategy(strategy)
    #engine.register_callback(PositionWeightPrinterCallback())

    engine.distribute()
    log = engine.run()
    
    analyzer = BacktestAnalyzer(log)
    analyzer.print()
    analyzer.export(path=path)

    visualizer = BasicVisualizer()
    visualizer.plot_log(log)

    visualizer.export(path=path)

if __name__ == '__main__':
    main(
        [
            "XBTUSD",
            "ETHUSD"
        ],
        [
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/10T/XBTUSD.csv",
            "/home/bellmanlabs/Data/bitmex/trade/ohlc/10T/ETHUSD.csv"
        ]
    )