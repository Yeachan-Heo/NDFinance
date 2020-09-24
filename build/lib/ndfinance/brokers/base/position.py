from ndfinance.brokers.base.asset import Asset
import numpy as np


class PositionLog:
    def __init__(self, amount, side, timestamp):
        self.timestamp = timestamp
        self.amount = amount
        self.side = side


class Position:
    def __init__(self, asset, avg_price, amount, side, timestamp):
        self.avg_price = avg_price
        self.amount = amount
        self.side = side
        self.asset:Asset = asset
        self.log = [PositionLog(amount, side, timestamp)]

        self.position_value = np.nan
        self.position_margin = np.nan
        self.position_pnl_percentage = np.nan
        self.position_margin = np.nan
        self.weight = np.nan

    def add_position(self, position):
        amount = position.amount
        side = position.side
        avg_price = position.avg_price

        new_amount = np.abs(self.amount * self.side + amount * side)
        sign_is_same = self.side == side

        self.log.append(position.log[-1])

        if sign_is_same:
            self.avg_price = (self.amount * self.avg_price + amount * avg_price) / new_amount
            self.amount = new_amount
            return 0

        if not sign_is_same:
            realized_pnl = self.unrealized_pnl * np.clip(np.abs(amount / self.amount), a_max = 1, a_min = 0)
            if np.abs(amount) > np.abs(self.amount):
                self.avg_price = avg_price
                self.side = side

            self.amount = new_amount
            return realized_pnl

    def evaluate(self, current_price):
        self.unrealized_pnl = (current_price - self.avg_price) * self.amount * self.side
        self.unrealized_pnl_percentage = (current_price / self.avg_price - 1) * self.side * 100
        self.position_value = current_price * self.amount
        self.position_margin = self.position_value * self.asset.margin_percentage

    def evaluate_weight(self, pv, pv_total, position_value):
        self.weight = self.position_value / pv
        self.weight_total = self.position_value / pv_total
        self.weight_position = self.position_value / position_value