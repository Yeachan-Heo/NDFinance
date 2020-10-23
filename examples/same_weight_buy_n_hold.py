from ndfinance.brokers.backtest import *
from ndfinance.core import BacktestEngine
from ndfinance.analysis.backtest.analyzer import BacktestAnalyzer
from ndfinance.analysis.technical import RateOfChange
from ndfinance.visualizers.backtest_visualizer import BasicVisualizer
from ndfinance.strategies.basic import SameWeightBuyHold
from ndfinance import reporters
import matplotlib.pyplot as plt


def main(tickers, name, benchmark, **kwargs):
    path="./bt_results/same_weight_bnh/"
    dp = BacktestDataProvider()
    dp.add_fdr_tickers(*tickers)
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
    
    reporters.make_html(log, benchmark, output=f"{name}_bnh.html")

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
            "BABA",
        ],
        "FANG",
        "^IXIC"

    )