import datetime
from enum import Enum

import pandas as pd

from poor_trader import utils, config

from poor_trader.backtesting.entity import EquityCurve, Account


class EquityCurveKey(Enum):
    EQUITY = 'Equity'
    CASH = 'Cash'
    DRAWDOWN = 'Drawdown'
    DRAWDOWN_PERCENT = 'DrawdownPercent'


EQUITY_CURVE_COLUMNS = [_.value for _ in EquityCurveKey]


class DefaultEquityCurve(EquityCurve):

    def __init__(self, dates=None, equity=None, cash=None, df=None):
        super().__init__(dates, equity, cash)
        self.df = df if df is not None else pd.DataFrame(columns=EQUITY_CURVE_COLUMNS)

    def update(self, date, account: Account):
        if len(self.df.index.values) == 0:
            earlier = pd.to_datetime(date) - datetime.timedelta(days=1)
            self.df.loc[earlier] = pd.Series()
            self.df.loc[earlier, EquityCurveKey.EQUITY.value] = account.starting_balance
            self.df.loc[earlier, EquityCurveKey.CASH.value] = account.starting_balance

        self.df.loc[date] = pd.Series()
        self.df.loc[date, EquityCurveKey.EQUITY.value] = account.equity
        self.df.loc[date, EquityCurveKey.CASH.value] = account.cash

        self.df[EquityCurveKey.DRAWDOWN.value] = self.df[EquityCurveKey.EQUITY.value].expanding(1).apply(
            lambda d: -(d.max()-d[-1]))
        self.df[EquityCurveKey.DRAWDOWN_PERCENT.value] = self.df[EquityCurveKey.EQUITY.value].expanding(1).apply(
            lambda d: -(100 * (d.max()-d[-1]) / d.max()))
        self.df = utils.round_df(self.df)

    def get_dates(self):
        return self.df.index.values

    def get_equity(self, date=None):
        return self.df.loc[date][EquityCurveKey.EQUITY.value]

    def get_cash(self, date=None):
        return self.df.loc[date][EquityCurveKey.CASH.value]

    def get_drawdown(self, date=None):
        return self.df.loc[date][EquityCurveKey.DRAWDOWN.value]

    def get_drawdown_percent(self, date=None):
        return self.df.loc[date][EquityCurveKey.DRAWDOWN_PERCENT.value]

    def save_to_file(self, dir_path):
        utils.makedirs(dir_path)
        self.df.to_pickle(dir_path / 'equity_curve.{}'.format(config.PICKLE_EXTENSION))
