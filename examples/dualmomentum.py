from ndfinance.brokers.backtest import *
from ndfinance.core import BacktestEngine
from ndfinance.analysis.backtest.analyzer import BacktestAnalyzer
from ndfinance.analysis.technical import RateOfChange
from ndfinance.visualizers.backtest_visualizer import BasicVisualizer
from ndfinance.strategies.trend import ActualMomentumStratagy
from ndfinance.callbacks import PositionWeightPrinterCallback
from ndfinance import reporters
import matplotlib.pyplot as plt


def main(tickers, name="NAME", n=200, momentum_threshold=1, rebalance_period=TimeFrames.day * 28):
    dp = BacktestDataProvider()
    dp.add_yf_tickers(*tickers)
    dp.add_technical_indicators(tickers, [TimeFrames.day], [RateOfChange(n)])

    indexer = TimeIndexer(dp.get_shortest_timestamp_seq())
    dp.set_indexer(indexer)
    dp.cut_data()

    brk = BacktestBroker(dp, initial_margin=10000)
    [brk.add_asset(Asset(ticker=ticker)) for ticker in tickers]

    strategy = ActualMomentumStratagy(
        momentum_threshold=momentum_threshold,
        rebalance_period=rebalance_period,
        momentum_label=f"ROCR{n}",
    )

    engine = BacktestEngine()
    engine.register_broker(brk)
    engine.register_strategy(strategy)
    log = engine.run()
    
    reporters.make_html(log, "^IXIC", output=f"{name}_dualmomentum.html")

if __name__ == '__main__':
    universe_fang_plus = [
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
    
    main(universe_fang_plus, name="FANG+")