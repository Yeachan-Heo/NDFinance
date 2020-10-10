from ndfinance.brokers.backtest import *
from ndfinance.core import BacktestEngine
from ndfinance.analysis.backtest.analyzer import BacktestAnalyzer
from ndfinance.analysis.technical import RateOfChange
from ndfinance.visualizers.backtest_visualizer import BasicVisualizer
from ndfinance.strategies.trend import ActualMomentumStratagy
from ndfinance.callbacks import PositionWeightPrinterCallback
import matplotlib.pyplot as plt


def main(tickers, n=200, momentum_threshold=1, rebalance_period=TimeFrames.day * 28, path="./bt_results/actualmomentum/"):
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
    
    analyzer = BacktestAnalyzer(log)
    analyzer.print()
    analyzer.export(path=path)

    visualizer = BasicVisualizer()
    visualizer.plot_log(log)

    visualizer.export(path=path)

if __name__ == '__main__':
    universe_ndx = [x[4:] for x in """
    atvi
    adbe
    amd
    alxn
    algn
    goog
    googl
    amzn
    amgn
    adi
    anss
    aapl
    amat
    asml
    adsk
    adp
    bidu
    biib
    bmrn
    bkng
    avgo
    cdns
    cdw
    cern
    chtr
    chkp
    ctas
    csco
    ctxs
    ctsh
    cmcsa
    cprt
    cost
    csx
    dxcm
    docu
    dltr
    ebay
    ea
    exc
    expe
    fb
    fast
    fisv
    fox
    foxa
    gild
    idxx
    ilmn
    incy
    intc
    intu
    isrg
    jd
    klac
    lrcx
    lbtya
    lbtyk
    lulu
    mar
    mxim
    meli
    mchp
    mu
    msft
    mrna
    mdlz
    mnst
    ntes
    nflx
    nvda
    nxpi
    orly
    pcar
    payx
    pypl
    pep
    pdd
    qcom
    regn
    rost
    sgen
    siri
    swks
    splk
    sbux
    snps
    tmus
    ttwo
    tsla
    txn
    khc
    tcom
    ulta
    vrsn
    vrsk
    vrtx
    wba
    wdc
    wday
    xel
    xlnx
    zm
    """.split("\n")][1:-1]
    
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
    
    main(universe_fang_plus, path="./bt_results/actualmomentum/fang_plus/")
    main(universe_ndx, path="./bt_results/actualmomentum/ndx/")