from ndfinance.brokers.base import *
import numpy as np

class WithDrawTypes():
    percentage = "percentage"
    initial_margin = "initial_margin"
    constant = "constant"
    possible_modes = ["percentage", "initial_margin", "constant"]


class WithDrawConfig():
    def __init__(self, use=False, mode=None, amount=None, percentage=None, period=None, withdraw_account=None):
        self._use = use
        self._mode = mode
        self._amount = amount if amount is None else np.float64(amount)
        self._percentage = percentage if percentage is None else np.float64(percentage)
        self._period = period if period is None else np.float64(percentage)
        self._withdraw_account = withdraw_account

    def set_period(self, period):
        self._period = np.float64(period)

    def use_withdraw(self, use=True):
        self._use = use

    def set_mode(self, mode):
        self._mode = mode

    def set_percentage(self, percentage):
        self._percentage = np.float64(percentage)

    def set_amount(self, amount):
        self._amount = np.float64(amount)

    def check_valid(self):
        if self._use:
            if self._mode is None:
                raise ValueError(
                    f"if you want to use withdraw, you have to set withdraw mode via WithDrawConfig.set_mode(mode:str)")
            if self._period is None:
                raise ValueError(
                    f"if you want to use withdraw, you have to set withdraw period via WithDrawConfig.set_period(mode:str)"
                )

        assert self._mode in WithDrawTypes.possible_modes, \
            f"Mode must in {WithDrawTypes.possible_modes}, not {self._mode}"
        assert not ((self._mode is WithDrawTypes.constant) and (
                    self._amount is None)),\
            f"current withdraw mode is {WithDrawTypes.constant} but WithDrawConfig._amount is None. you can set this via WithDrawConfig.set_amount(amount:float)"
        assert not ((self._mode is WithDrawTypes.percentage) and (
                    self._percentage is None)), \
            f"current withdraw mode is {WithDrawTypes.constant} but WithDrawConfig._percentage is None. you can set this via WithDrawConfig.set_percentage(amount:float)"
        return self

    @property
    def mode(self):
        return self._mode

    @property
    def use(self):
        return self._use