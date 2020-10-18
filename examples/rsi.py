from ndfinance.brokers.backtest import *
from ndfinance.core import BacktestEngine
from ndfinance.analysis.backtest.analyzer import BacktestAnalyzer
from ndfinance.analysis.technical import RSI
from ndfinance.visualizers.backtest_visualizer import BasicVisualizer
from ndfinance.strategies.basic import OscillatorStrategy
from ndfinance.callbacks import PositionWeightPrinterCallback
import matplotlib.pyplot as plt


def main(ticker, n=14, path="./bt_results/rsi/", timecut_days=7):
    dp = BacktestDataProvider()
    dp.add_yf_tickers(ticker)
    dp.add_technical_indicators([ticker], [TimeFrames.day], [RSI(n)])

    indexer = TimeIndexer(dp.get_shortest_timestamp_seq())
    dp.set_indexer(indexer)
    dp.cut_data()

    brk = BacktestBroker(dp, initial_margin=10000)
    brk.add_asset(Asset(ticker=ticker))

    strategy = OscillatorStrategy(
        breakout_threshold=50, oversold_threshold=30, overbought_threshold=70, 
        osc_label=f"RSI{n}", use_short=False, 
        use_time_cut=False, timecut_params={"days" : timecut_days},
        use_stop_loss=True, stop_loss_params={"threshold": 5},
        use_n_perc_rule=False, n_perc_params={"n_percent" : 5, "loss_cut_percent" : 10}
    )

    engine = BacktestEngine()
    engine.register_broker(brk)
    engine.register_strategy(strategy)
    log = engine.run()
    
    analyzer = BacktestAnalyzer(log)
    analyzer.print()
    analyzer.export(path=path)

    visualizer = BasicVisualizer()
    visualizer.plot_log(log)

    visualizer.export(path=path)


if __name__ == "__main__":
    main("^GSPC",  path="./bt_results/rsi/gspc/")
    main("^IXIC",  path="./bt_results/rsi/ixic/")