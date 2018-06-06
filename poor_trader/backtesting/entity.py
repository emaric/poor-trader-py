import abc
from enum import Enum


class Action(Enum):
    OPEN = 'OPEN'
    CLOSE = 'CLOSE'


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

    def __init__(self, account: Account, name=None, strategies=list()):
        self.account = account
        self.name = name or self.__class__.__name__
        self.strategies = strategies

    @abc.abstractmethod
    def close(self, date, symbols):
        raise NotImplementedError

    @abc.abstractmethod
    def open(self, date, symbols):
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

    @abc.abstractmethod
    def get_positions(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_transactions(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_equity(self, date):
        raise NotImplementedError

    @abc.abstractmethod
    def get_cash(self, date):
        raise NotImplementedError

    @abc.abstractmethod
    def get_drawdown(self, date):
        raise NotImplementedError

    @abc.abstractmethod
    def get_drawdown_percent(self, date):
        raise NotImplementedError
