import abc
from enum import Enum, auto


class Action(Enum):
    OPEN = auto()
    CLOSE = auto()


class Backtester(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def run(self, market, start=None, end=None):
        raise NotImplementedError


class Account(object):
    def __init__(self, starting_balance, cash=None, equity=None):
        self.starting_balance = starting_balance
        self.cash = cash or starting_balance
        self.equity = equity or starting_balance
        self.buying_power = self.cash


class Transaction(object):
    def __init__(self, action, date, symbol, shares, price, value, tags):
        self.action = action
        self.date = date
        self.symbol = symbol
        self.shares = shares
        self.price = price
        self.value = value
        self.tags = tags


class Position(object):
    def __init__(self, entry_date, exit_date, direction, symbol, shares, price, value):
        self.entry_date = entry_date
        self.exit_date = exit_date
        self.direction = direction
        self.symbol = symbol
        self.shares = shares
        self.price = price
        self.value = value


class PositionSizing(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, name='PositionSizing'):
        self.name = name

    @abc.abstractmethod
    def calculate_shares(self, date, symbol, account):
        raise NotImplementedError

    @abc.abstractmethod
    def calculate_total_risk(self, price, shares, account):
        raise NotImplementedError


class EquityCurve(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, dates=None, equity=None, cash=None):
        self.dates = dates,
        self.equity = equity
        self.cash = cash

    @abc.abstractmethod
    def update(self, date, account: Account):
        raise NotImplementedError

    @abc.abstractmethod
    def get_dates(self):
        return self.dates

    @abc.abstractmethod
    def get_equity(self, date=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_cash(self, date=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_drawdown(self, date=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_drawdown_percent(self, date=None):
        raise NotImplementedError

    @abc.abstractmethod
    def save_to_file(self, dir_path):
        raise NotImplementedError


class Broker(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, name='Broker'):
        self.name = name

    @abc.abstractmethod
    def calculate_buy_value(self, price, shares):
        raise NotImplementedError

    @abc.abstractmethod
    def calculate_sell_value(self, price, shares):
        raise NotImplementedError


class Portfolio(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, account: Account, equity_curve: EquityCurve, name=None, strategies=list()):
        self.account = account
        self.equity_curve = equity_curve
        self.name = name or self.__class__.__name__
        self.strategies = strategies

    def __get_tags__(self, direction, date, symbol, start=None):
        tags = []
        for strategy in self.strategies:
            names = strategy.get_indicator_names(direction=direction, date=date, symbol=symbol, start=start)
            tags = tags + names
        tags = list(set(tags))
        sorted(tags)
        return ' '.join(tags)

    @abc.abstractmethod
    def close(self, position: Position, tags: str):
        raise NotImplementedError

    @abc.abstractmethod
    def open(self, date, symbol, tags: str):
        raise NotImplementedError

    @abc.abstractmethod
    def close_positions(self, date, symbols):
        raise NotImplementedError

    @abc.abstractmethod
    def open_positions(self, date, symbols):
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, date, symbols):
        self.close_positions(date, symbols)
        self.open_positions(date, symbols)
        self.equity_curve.update(date, self.account)

    @abc.abstractmethod
    def get_positions(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_transactions(self):
        raise NotImplementedError


