from distutils.core import setup

setup(
    name='NDFinance',
    version='0.0.1',
    packages=['ndfinance', 'ndfinance.core', 'ndfinance.data', 'ndfinance.data.crawlers',
              'ndfinance.data.crawlers.naver', 'ndfinance.data.crawlers.bitmex', 'ndfinance.utils',
              'ndfinance.utils.backtest', 'ndfinance.brokers', 'ndfinance.brokers.base', 'ndfinance.brokers.backtest',
              'ndfinance.loggers', 'ndfinance.loggers.backtest', 'ndfinance.analysis', 'ndfinance.analysis.backtest',
              'ndfinance.analysis.technical', 'ndfinance.analysis.machine_learning',
              'ndfinance.analysis.reinforcement_learning', 'ndfinance.analysis.reinforcement_learning.environments',
              'ndfinance.callbacks', 'ndfinance.strategies', 'ndfinance.strategies.basic', 'ndfinance.strategies.trend',
              'ndfinance.strategies.utils', 'ndfinance.visualizers'],
    url='https://github.com/Yeachan-Heo/NDFinance',
    license='MIT',
    author='Yeachan-Heo',
    author_email='rlstart@kakao.com',
    description='Backtesting Engine Written in Python, Powered by Ray'
)
