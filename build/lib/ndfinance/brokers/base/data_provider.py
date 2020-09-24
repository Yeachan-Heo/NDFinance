class OHLCVT:
    open = "open"
    high = "high"
    low = "low"
    close = "close"
    volume = "volume"
    timestamp = "timestamp"

class DataProvider:
    def __init__(self):
        pass

    def current(self, *args, **kwargs):
        return self.historical(*args, **kwargs)[-1]

    def historical(self, *args, **kwargs):
        raise NotImplementedError


