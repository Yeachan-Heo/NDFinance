import numpy as np
from talib import abstract as ta

def TA_BBANDS(prices:np.ndarray,
              timeperiod:int=5,
              nbdevup:int=2.,
              nbdevdn:int=2.,
              matype:int=0):

    up, middle, low = ta.BBANDS(prices,
                                timeperiod,
                                nbdevup,
                                nbdevdn,
                                matype)
    ch = (up - low) / middle
    b = (prices - low) / (up - low)
    return up, middle, low, ch, b


class TechnicalIndicator:
    def __init__(self):
        self.name = self.make_name()

    def make_name(self) -> str:
        return ""

    def __call__(self, data):
        return data


class SimpleMovingAverage(TechnicalIndicator):
    def __init__(self, period):
        self.period = period
        super(SimpleMovingAverage, self).__init__()

    def make_name(self) -> str:
        return f"SMA{self.period}"

    def __call__(self, data:np.ndarray):
        return ta.SMA(data["close"], timeperiod=self.period)


