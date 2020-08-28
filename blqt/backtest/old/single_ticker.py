import pandas as pd
import numpy as np


class FinancialProduct:
    def __init__(self, ticker, fee, tick, tick_value, slippage, min_amount,
                 margin_requirement, margin_requirement_maintain,
                 ):
        self.ticker = ticker

        self.tick_value = tick_value

        self.mr = margin_requirement
        self.mrm = margin_requirement_maintain

        self.slippage = slippage
        self.tick = tick
        self.fee = fee

        self.min_amount = min_amount

class Position:
    def __init__(self, product: FinancialProduct, amount, avg_price=None):
        self.amount = amount
        self.bidorask = np.sign(amount)
        self.product = product
        self.avg_price = avg_price
        if self.avg_price is None:
            self.avg_price = (self.product.bid_price if self.bidorask == 1 else self.product.ask_price)
        self.init_pos_value()
        self.update_value()

    def init_pos_value(self):
        self.first_pos_value = self.avg_price * self.amount

    def update_value(self):
        self.product.update_data()
        self.pos_value = (self.product.bid_price if self.bidorask == -1 else self.product.ask_price) * self.amount
        self.pal = self.pos_value - self.first_pos_value
        self.pal_perc = (self.pos_value / self.first_pos_value - 1) * self.bidorask

    def add(self, pos):
        sign_is_same = np.sign(pos.amount) == np.sign(self.amount)
        n = self.amount + pos.amount
        if self.amount == 0:
            return 0, pos
        if sign_is_same:
            avg_price = (self.amount * self.avg_price + pos.amount * pos.avg_price) / n
            new_pos = Position(self.product, n, avg_price)
            return 0, new_pos
        if not sign_is_same:
            realized_pal = self.pal * np.clip(np.abs(pos.amount / self.amount), a_max=1, a_min=0)
            avg_price = pos.avg_price if np.abs(pos.amount) > np.abs(self.amount) else self.avg_price
            new_pos = Position(self.product, n, avg_price)
            return realized_pal, new_pos
        raise ValueError
