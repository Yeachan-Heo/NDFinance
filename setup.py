from setuptools import setup

setup(
    name='ndfinance',
    version='',
    packages=['ndfinance', 'ndfinance.core', 'ndfinance.data', 'ndfinance.data.crawlers',
              'ndfinance.data.crawlers.naver', 'ndfinance.data.crawlers.bitmex',
              'ndfinance.data.crawlers.fx_fut_data_ts_room', 'ndfinance.utils', 'ndfinance.brokers',
              'ndfinance.brokers.base', 'ndfinance.brokers.backtest', 'ndfinance.loggers', 'ndfinance.loggers.backtest',
              'ndfinance.analysis', 'ndfinance.analysis.backtest', 'ndfinance.analysis.technical',
              'ndfinance.analysis.machine_learning', 'ndfinance.analysis.machine_learning.rl_envs',
              'ndfinance.callbacks', 'ndfinance.strategies', 'ndfinance.strategies.basic', 'ndfinance.visualizers'],
    url='',
    license='',
    author='Yeachan-Heo',
    author_email='',
    description=''
)
