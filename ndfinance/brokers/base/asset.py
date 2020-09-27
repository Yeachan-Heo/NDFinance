import numpy as np


class Asset:
    def __init__(self, ticker:str, slippage=0, fee=0, max_leverage=1, min_amount=1e-7):
        self.ticker = ticker
        self.slippage = slippage / 100
        self.fee = fee / 100
        self.max_leverage = max_leverage
        self.margin_percentage = 1 / max_leverage
        self.min_amount = min_amount

    def __str__(self):
        return f"ticker:{self.ticker},slippage:{self.slippage*100},fee:{self.fee*100},max_leverage:{self.max_leverage},min_amount:{self.min_amount},can_short:{self.can_short}"



