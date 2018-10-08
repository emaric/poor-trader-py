import pandas as pd

from poor_trader import utils
from poor_trader.market import Market
from poor_trader.backtesting.entity import PositionSizing
from poor_trader.screening import indicator
from poor_trader.screening.indicator import IndicatorFactory


class FixedFractional(PositionSizing):
    def __init__(self, market: Market, total_risk_pct=0.01, unit_risk=0.2, name=None):
        super().__init__(name or self.__class__.__name__)
        self.market = market
        self.total_risk_pct = total_risk_pct
        self.unit_risk = unit_risk

    def calculate_shares(self, date, symbol, account, use_boardlot=True, base_value=None):
        price = self.market.get_close(date, symbol)
        C = account.equity * self.total_risk_pct
        if base_value is not None:
            C = base_value * self.total_risk_pct
        R = price * self.unit_risk
        P = C / R
        shares = int(P)
        if use_boardlot:
            boardlot = utils.boardlot(price)
            shares = int(shares / boardlot) * boardlot
        return shares

    def calculate_total_risk(self, price, shares, account):
        R = price * self.unit_risk
        return shares * R


class ATRBased(PositionSizing):
    def __init__(self, market: Market, factory: IndicatorFactory, total_risk_pct=0.01, unit_risk=0.2, name=None):
        super().__init__(name or self.__class__.__name__)
        self.market = market
        self.total_risk_pct = total_risk_pct
        self.unit_risk = unit_risk
        self.atr_indicator = factory.create(indicator.ATR)

    def normalized_atr(self, date, symbol):
        atr_values = self.atr_indicator.get_attribute_value(symbol=symbol, key='ATR')
        indices = self.atr_indicator.get_attribute(key='ATR').get_indices(symbol=symbol)
        atr = pd.Series(atr_values, index=indices)
        normalized_atr = (atr-atr.min())/(atr.max()-atr.min())
        return normalized_atr.loc[date]

    def atr(self, date, symbol):
        return self.atr_indicator.get_attribute_value(date=date, symbol=symbol, key='ATR')

    def calculate_shares(self, date, symbol, account, use_boardlot=True):
        price = self.market.get_close(date, symbol)
        atr = self.atr(date, symbol)
        normal_atr = self.normalized_atr(date, symbol)
        C = account.equity * self.total_risk_pct
        # C = C / (atr / normal_atr)
        R = price * (atr / normal_atr)
        P = C / R
        shares = int(P)
        if use_boardlot:
            boardlot = utils.boardlot(price)
            shares = int(shares / boardlot) * boardlot
        return shares

    def calculate_total_risk(self, price, shares, account):
        R = price * self.unit_risk
        return shares * R


class RiskedBased(PositionSizing):
    def __init__(self, market: Market, total_risk_pct=0.01, unit_risk=0.2, name=None):
        super().__init__(name or self.__class__.__name__)
        self.market = market
        self.total_risk_pct = total_risk_pct
        self.unit_risk = unit_risk

    def calculate_shares(self, date, symbol, account, use_boardlot=True):
        price = self.market.get_close(date, symbol)
        C = account.equity * self.total_risk_pct
        #C = C / (40 * price)
        R = price * self.unit_risk
        P = C / (price * 40)
        shares = int(P)
        if use_boardlot:
            boardlot = utils.boardlot(price)
            shares = int(shares / boardlot) * boardlot
        return shares

    def calculate_total_risk(self, price, shares, account):
        R = price * self.unit_risk
        return shares * R