from setuptools import setup

setup(
    name='ndfinance',
    version='0.0.0',
    packages=['ndfinance', 'ndfinance.core', 'ndfinance.data', 'ndfinance.data.crawlers',
              'ndfinance.data.crawlers.naver', 'ndfinance.data.crawlers.bitmex',
              'ndfinance.utils', 'ndfinance.brokers', 'ndfinance.utils.backtest',
              'ndfinance.brokers.base', 'ndfinance.brokers.backtest', 'ndfinance.loggers', 'ndfinance.loggers.backtest',
              'ndfinance.analysis', 'ndfinance.analysis.backtest', 'ndfinance.analysis.technical',
              'ndfinance.analysis.machine_learning', 'ndfinance.analysis.machine_learning.rl_envs',
              'ndfinance.callbacks', 'ndfinance.strategies', 'ndfinance.strategies.basic', 'ndfinance.strategies.trend', 'ndfinance.strategies.utils', 'ndfinance.visualizers'],
    url='https://github.com/Yeachan-Heo/NDFinance.git',
    license='MIT',
    author='Yeachan-Heo',
    author_email='rlstart@kakao.com',
    description='Backtest & ML/DL Quant analysis'
)
