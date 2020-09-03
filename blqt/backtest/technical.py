import numpy as np
from talib import abstract as ta
from talib.abstract import *

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