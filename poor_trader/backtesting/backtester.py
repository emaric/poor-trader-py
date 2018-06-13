from enum import Enum

import pandas as pd

from poor_trader import config, utils
from poor_trader.backtesting.entity import Position, Action, Backtester, Portfolio
from poor_trader.market import Market


class TransactionKey(Enum):
    ACTION = 'Action'
    DATE = 'Date'
    SYMBOL = 'Symbol'
    SHARES = 'Shares'
    PRICE = 'Price'
    VALUE = 'Value'
    TAGS = 'Tags'


class PositionKey(Enum):
    ENTRY_DATE = 'EntryDate'
    EXIT_DATE = 'ExitDate'
    DIRECTION = 'Direction'
    SYMBOL = 'Symbol'
    SHARES = 'Shares'
    PRICE = 'Price'
    VALUE = 'Value'


TRANSACTION_COLUMNS = [_.value for _ in TransactionKey]

POSITION_COLUMNS = [_.value for _ in PositionKey]


class PositionService(object):
    def __init__(self):
        self.df = pd.DataFrame(columns=POSITION_COLUMNS)

    def __find__(self, entry_date=None, direction=None, symbol=None):
        df = self.df.copy()
        df = df[df[PositionKey.ENTRY_DATE.value] == entry_date] if entry_date else df
        df = df[pd.isnull(df[PositionKey.EXIT_DATE.value])]
        df = df[df[PositionKey.DIRECTION.value] == direction] if direction else df
        df = df[df[PositionKey.SYMBOL.value] == symbol] if symbol else df
        if len(df.index.values) == 1:
            return df.index.values[0]
        elif len(df.index.values) == 0:
            return None
        else:
            raise NotImplementedError

    def save(self, position):
        index = self.__find__(entry_date=position.entry_date, direction=position.direction, symbol=position.symbol)
        if index is None:
            new_index = len(self.df.index.values)
            self.df.loc[new_index] = pd.Series()
            self.df.loc[new_index, PositionKey.ENTRY_DATE.value] = position.entry_date
            self.df.loc[new_index, PositionKey.DIRECTION.value] = position.direction
            self.df.loc[new_index, PositionKey.SYMBOL.value] = position.symbol
            index = new_index

        self.df.loc[index, PositionKey.EXIT_DATE.value] = position.exit_date
        self.df.loc[index, PositionKey.SHARES.value] = position.shares
        self.df.loc[index, PositionKey.PRICE.value] = position.price
        self.df.loc[index, PositionKey.VALUE.value] = position.value

    def get_open_positions(self):
        positions = []
        df_open = self.df[pd.isnull(self.df[PositionKey.EXIT_DATE.value])]
        for i in df_open.index.values:
            s_open = df_open.loc[i]
            position = Position(entry_date=s_open[PositionKey.ENTRY_DATE.value],
                                exit_date=s_open[PositionKey.EXIT_DATE.value],
                                direction=s_open[PositionKey.DIRECTION.value],
                                symbol=s_open[PositionKey.SYMBOL.value],
                                shares=s_open[PositionKey.SHARES.value],
                                price=s_open[PositionKey.PRICE.value],
                                value=s_open[PositionKey.VALUE.value])
            positions.append(position)
        return positions

    def get_open_symbols(self):
        return self.df[pd.isnull(self.df[PositionKey.EXIT_DATE.value])][PositionKey.SYMBOL.value].values

    def get_open_values(self):
        open_positions = self.get_open_positions()
        return sum([_.value for _ in open_positions])

    def save_to_file(self, dir_path):
        utils.makedirs(dir_path)
        self.df.to_pickle(dir_path / 'positions.{}'.format(config.PICKLE_EXTENSION))


class TransactionService(object):
    def __init__(self):
        self.df = pd.DataFrame(columns=TRANSACTION_COLUMNS)

    def size(self):
        return len(self.df.index.values)

    def add(self, action, date, symbol, price, shares, value, tags):
        index = self.size()
        self.df.loc[index] = pd.Series()
        self.df.loc[index, TransactionKey.ACTION.value] = action
        self.df.loc[index, TransactionKey.DATE.value] = date
        self.df.loc[index, TransactionKey.SYMBOL.value] = symbol
        self.df.loc[index, TransactionKey.PRICE.value] = price
        self.df.loc[index, TransactionKey.SHARES.value] = shares
        self.df.loc[index, TransactionKey.VALUE.value] = value
        self.df.loc[index, TransactionKey.TAGS.value] = tags

    def open(self, date, symbol, price, shares, value, tags):
        self.add(Action.OPEN, date, symbol, price, shares, value, tags)

    def close(self, date, symbol, price, shares, value, tags):
        self.add(Action.CLOSE, date, symbol, price, shares, value, tags)

    def save_to_file(self, dir_path):
        utils.makedirs(dir_path)
        self.df.to_pickle(dir_path / 'transactions.{}'.format(config.PICKLE_EXTENSION))


class DataFrameBacktester(Backtester):
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def run(self, market: Market, start=None, end=None):
        for date in market.get_dates():
            if start is not None and pd.to_datetime(date) < start:
                continue
            if end is not None and pd.to_datetime(date) > end:
                break
            symbols = market.get_symbols(date)
            self.portfolio.update(date, symbols)
        return self.portfolio.equity_curve


