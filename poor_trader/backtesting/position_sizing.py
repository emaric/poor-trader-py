from poor_trader.market import Market
from poor_trader.backtesting.entity import PositionSizing


class EquityPercentage(PositionSizing):
    def __init__(self, market: Market, total_risk_pct=0.01, unit_risk=0.2, name=None):
        super().__init__(name or self.__class__.__name__)
        self.market = market
        self.total_risk_pct = total_risk_pct
        self.unit_risk = unit_risk

    def calculate_shares(self, date, symbol, account):
        price = self.market.get_close(date, symbol)
        C = account.equity * self.total_risk_pct
        R = price * self.unit_risk
        P = C / R
        return int(P)

    def calculate_total_risk(self, price, shares, account):
        R = price * self.unit_risk
        return shares * R
