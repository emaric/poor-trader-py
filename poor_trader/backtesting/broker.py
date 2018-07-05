from poor_trader.backtesting.entity import Broker


class PSEDefaultBroker(Broker):
    def __init__(self, name=None):
        super().__init__(name or self.__class__.__name__)

    def calculate_commission(self, price, shares, commission=0.0025):
        value = price * shares
        com = value * commission
        return com if com > 20 else 20

    def calculate_buying_fees(self, price, shares, commission=0.0025, vat_on_commission=0.12, pse_trans_fee=0.00005, sccp=0.0001):
        value = price * shares
        com = self.calculate_commission(price, shares, commission=commission)
        vat_com = com * vat_on_commission
        trans = value * pse_trans_fee
        sccp_fee = value * sccp
        return com + vat_com + trans + sccp_fee

    def calculate_selling_fees(self, price, shares, sales_tax=0.006):
        tax = price * shares * sales_tax
        return self.calculate_buying_fees(price, shares) + tax

    def calculate_buy_value(self, price, shares):
        if shares <= 0:
            return 0.0
        return price * shares + self.calculate_buying_fees(price, shares)

    def calculate_sell_value(self, price, shares):
        if shares <= 0:
            return 0.0
        return price * shares - self.calculate_selling_fees(price, shares)
