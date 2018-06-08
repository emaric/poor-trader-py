import datetime
import os
from enum import Enum

import pandas as pd

from poor_trader import config, utils
from poor_trader.backtesting.broker import COLFinancial
from poor_trader.backtesting.entity import Backtester, Portfolio, Account, PositionSizing, Broker, Action
from poor_trader.backtesting.position_sizing import EquityPercentage
from poor_trader.charting import equity_curve as charting_equity_curve
from poor_trader.charting.entity import EquityCurveChart, EquityCurveItem, EquityCurveKey
from poor_trader.market import Market, pkl_to_market
from poor_trader.screening.entity import Direction
from poor_trader.screening.indicator import PickleIndicatorFactory
from poor_trader.screening.strategy import Strategy, DonchianChannel


class TransactionEnum(Enum):
    ACTION = 'Action'
    DATE = 'Date'
    SYMBOL = 'Symbol'
    SHARES = 'Shares'
    PRICE = 'Price'
    VALUE = 'Value'
    TAGS = 'Tags'


class PositionEnum(Enum):
    DIRECTION = 'Direction'
    SYMBOL = 'Symbol'
    SHARES = 'Shares'
    PRICE = 'Price'
    VALUE = 'Value'


EQUITY_CURVE_COLUMNS = [_.value for _ in EquityCurveKey]
TRANSACTION_COLUMNS = [_.value for _ in TransactionEnum]
POSITION_COLUMNS = [_.value for _ in PositionEnum]


class DataFrameBacktester(Backtester):
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def run(self, market: Market, start=None, end=None):
        df = pd.DataFrame(columns=EQUITY_CURVE_COLUMNS)
        for date in market.get_dates():
            if start is not None and pd.to_datetime(date) < start:
                continue
            if end is not None and pd.to_datetime(date) > end:
                break
            symbols = market.get_symbols(date)
            self.portfolio.update(date, symbols)
            df.loc[date] = pd.Series()
            df.loc[date, EquityCurveKey.EQUITY.value] = self.portfolio.get_equity(date)
            df.loc[date, EquityCurveKey.CASH.value] = self.portfolio.get_cash(date)
            df.loc[date, EquityCurveKey.DRAWDOWN.value] = self.portfolio.get_drawdown(date)
            df.loc[date, EquityCurveKey.DRAWDOWN_PERCENT.value] = self.portfolio.get_drawdown_percent(date)
        return utils.round_df(df)


class DataFramePortfolio(Portfolio):
    EQUITY_CURVE_FILENAME = 'equity_curve.pkl'
    POSITIONS_FILENAME = 'positions.pkl'
    TRANSACTIONS_FILENAME = 'transactions.pkl'

    def __init__(self, account: Account,
                 dir_path,
                 indicators_dir_path,
                 market: Market,
                 position_sizing: PositionSizing,
                 broker: Broker,
                 name=None, strategies=list()):
        super().__init__(account, name, strategies)
        self.dir_path = dir_path
        self.indicators_dir_path = indicators_dir_path
        self.market = market
        self.position_sizing = position_sizing
        self.broker = broker
        self.strategies = strategies if len(strategies) > 0 else self.__init_strategies__()
        self.positions = pd.DataFrame(columns=POSITION_COLUMNS)
        self.transactions = pd.DataFrame(columns=TRANSACTION_COLUMNS)
        self.equity_curve = pd.DataFrame(columns=EQUITY_CURVE_COLUMNS)

    def __init_strategies__(self):
        strategy_classes = Strategy.__subclasses__()
        factory = PickleIndicatorFactory(self.indicators_dir_path, self.market)
        return [strategy_class(factory) for strategy_class in strategy_classes]

    def close(self, date, symbols):
        df = pd.DataFrame(columns=TRANSACTION_COLUMNS)
        for symbol in symbols:
            index = symbols.index(symbol)
            df.loc[index] = pd.Series()
            df.loc[index][TransactionEnum.ACTION.value] = Action.CLOSE
            df.loc[index][TransactionEnum.DATE.value] = pd.to_datetime(date).strftime(config.DATETIME_FORMAT)
            df.loc[index][TransactionEnum.SYMBOL.value] = symbol
            df.loc[index][TransactionEnum.PRICE.value] = self.market.get_close(date, symbol)
        return df

    def open(self, date, symbols):
        df = pd.DataFrame(columns=TRANSACTION_COLUMNS)
        for symbol in symbols:
            index = symbols.index(symbol)
            df.loc[index] = pd.Series()
            df.loc[index][TransactionEnum.ACTION.value] = Action.OPEN
            df.loc[index][TransactionEnum.DATE.value] = pd.to_datetime(date).strftime(config.DATETIME_FORMAT)
            df.loc[index][TransactionEnum.SYMBOL.value] = symbol
            df.loc[index][TransactionEnum.PRICE.value] = self.market.get_close(date, symbol)
        return df

    def __apply_close_position_sizing__(self, close_transactions):
        if not close_transactions.empty:
            for index in close_transactions.index.values:
                symbol = close_transactions.loc[index][TransactionEnum.SYMBOL.value]
                position = self.positions[self.positions[PositionEnum.SYMBOL.value] == symbol]
                shares = position[PositionEnum.SHARES.value].values[0]
                close_transactions.loc[index][TransactionEnum.SHARES.value] = shares
            price = close_transactions[TransactionEnum.PRICE.value]
            shares = close_transactions[TransactionEnum.SHARES.value]
            close_transactions[TransactionEnum.VALUE.value] = price * shares

    def __apply_open_position_sizing__(self, open_transactions):
        if not open_transactions.empty:
            open_transactions[TransactionEnum.SHARES.value] = open_transactions.apply(
                lambda t: self.position_sizing.calculate_shares(t[TransactionEnum.DATE.value],
                                                                t[TransactionEnum.SYMBOL.value],
                                                                self.account), axis=1)
            price = open_transactions[TransactionEnum.PRICE.value]
            shares = open_transactions[TransactionEnum.SHARES.value]
            open_transactions[TransactionEnum.VALUE.value] = price * shares

    def __apply_boardlot__(self, open_transactions):
        if not open_transactions.empty:
            boardlot = open_transactions.apply(lambda t: utils.boardlot(t[TransactionEnum.PRICE.value]), axis=1)
            shares = open_transactions[TransactionEnum.SHARES.value]
            open_transactions[TransactionEnum.SHARES.value] = (shares / boardlot).astype(int) * boardlot
            price = open_transactions[TransactionEnum.PRICE.value]
            shares = open_transactions[TransactionEnum.SHARES.value]
            open_transactions[TransactionEnum.VALUE.value] = price * shares

    def __apply_broker_values__(self, open_transactions, action: Action):
        if not open_transactions.empty:
            calculate_method = self.broker.calculate_buy_value if action == Action.OPEN else self.broker.calculate_sell_value
            open_transactions[TransactionEnum.VALUE.value] = open_transactions.apply(
                lambda t: calculate_method(t[TransactionEnum.PRICE.value],
                                           t[TransactionEnum.SHARES.value]), axis=1)

    def __add_tags__(self, transactions, indicator_names_getter):
        if not transactions.empty:
            transactions[TransactionEnum.TAGS.value] = transactions.apply(
                lambda t: ' '.join(indicator_names_getter(t[TransactionEnum.DATE.value],
                                                          t[TransactionEnum.SYMBOL.value])), axis=1)

    def update_positions(self, new_transactions, direction, date=None):
        if new_transactions is not None and not new_transactions.empty:
            symbols = new_transactions[TransactionEnum.SYMBOL.value].values

            existing_positions = self.positions[self.positions[PositionEnum.SYMBOL.value].isin(symbols)]
            if direction is not None:
                existing_positions = existing_positions[existing_positions[PositionEnum.DIRECTION.value] == direction]

            new_symbols = [_ for _ in symbols if _ not in self.positions[self.positions[PositionEnum.DIRECTION.value] == direction][PositionEnum.SYMBOL.value].values]
            if len(new_symbols) > 0:
                for symbol in new_symbols:
                    index = len(self.positions.index.values)
                    new_transaction = new_transactions.loc[new_transactions[TransactionEnum.SYMBOL.value] == symbol]
                    self.positions.loc[index] = pd.Series()
                    self.positions.loc[index, PositionEnum.DIRECTION.value] = direction
                    self.positions.loc[index, PositionEnum.SYMBOL.value] = symbol
                    self.positions.loc[index, PositionEnum.SHARES.value] = new_transaction[TransactionEnum.SHARES.value].values[0]
                    self.positions.loc[index, PositionEnum.PRICE.value] = new_transaction[TransactionEnum.PRICE.value].values[0]
                    self.positions.loc[index, PositionEnum.VALUE.value] = new_transaction[TransactionEnum.VALUE.value].values[0]

            for index in existing_positions.index.values:
                symbol = self.positions.loc[index][PositionEnum.SYMBOL.value]
                position_shares = self.positions.loc[index][PositionEnum.SHARES.value]
                transaction_shares = new_transactions[new_transactions[TransactionEnum.SYMBOL.value] == symbol][TransactionEnum.SHARES.value].values[0]
                is_open_transaction = new_transactions[new_transactions[TransactionEnum.SYMBOL.value] == symbol][TransactionEnum.ACTION.value].values[0] == Action.OPEN
                transaction_shares = transaction_shares if is_open_transaction else -transaction_shares
                new_shares = position_shares + transaction_shares
                self.positions.loc[index, PositionEnum.SHARES.value] = new_shares

        if date is not None and not self.positions.empty:
            self.positions[PositionEnum.PRICE.value] = self.positions.apply(
                lambda p: self.market.get_close(end=date, symbol=p[PositionEnum.SYMBOL.value]).dropna().values[-1], axis=1)
            self.positions[PositionEnum.VALUE.value] = self.positions.apply(
                lambda p: self.broker.calculate_sell_value(p[PositionEnum.PRICE.value], p[PositionEnum.SHARES.value]), axis=1)
        self.__remove_empty_positions__()

    def update_account(self, transactions):
        close_transactions = transactions[transactions[TransactionEnum.ACTION.value] == Action.CLOSE]
        open_transactions = transactions[transactions[TransactionEnum.ACTION.value] == Action.OPEN]
        if not close_transactions.empty:
            self.account.cash = self.account.cash + close_transactions[TransactionEnum.VALUE.value].sum()
        if not open_transactions.empty:
            self.account.cash = self.account.cash - open_transactions[TransactionEnum.VALUE.value].sum()
        self.account.equity = self.account.cash + self.positions[PositionEnum.VALUE.value].sum()

    def open_positions(self, date, symbols):
        if self.account.cash > 0:
            closed_symbols = self.transactions[(pd.to_datetime(self.transactions[TransactionEnum.DATE.value]) == pd.to_datetime(date))
                                               & (self.transactions[TransactionEnum.ACTION.value] == Action.CLOSE)][TransactionEnum.SYMBOL.value].values
            open_symbols = self.positions[PositionEnum.SYMBOL.value].values
            for strategy in self.strategies:
                long_symbols = [_ for _ in symbols if strategy.is_long(date, _) and _ not in self.positions[PositionEnum.SYMBOL.value].values and _ not in closed_symbols and _ not in open_symbols]
                open_transactions = self.open(date, long_symbols)
                self.__apply_open_position_sizing__(open_transactions)
                self.__apply_boardlot__(open_transactions)
                self.__apply_broker_values__(open_transactions, Action.OPEN)
                while self.account.cash < open_transactions[TransactionEnum.VALUE.value].sum():
                    open_transactions = open_transactions[open_transactions[TransactionEnum.VALUE.value] > open_transactions[TransactionEnum.VALUE.value].min()]
                if not open_transactions.empty:
                    self.__add_tags__(open_transactions, strategy.get_long_indicator_names)
                    self.transactions = self.transactions.append(open_transactions, ignore_index=True)
                    self.update_positions(open_transactions, Direction.LONG)
                    self.update_account(open_transactions)

    def __remove_empty_positions__(self):
        if not self.positions[self.positions[PositionEnum.SHARES.value] < 0].empty:
            raise RuntimeError
        self.positions = self.positions[self.positions[PositionEnum.SHARES.value] > 0]

    def close_positions(self, date, symbols):
        if not self.positions.empty:
            open_symbols = [_ for _ in symbols if _ in self.positions[PositionEnum.SYMBOL.value].values]
            for strategy in self.strategies:
                close_transactions = self.close(date, [_ for _ in open_symbols if strategy.is_short(date=date, symbol=_)])
                if not close_transactions.empty:
                    self.__apply_close_position_sizing__(close_transactions)
                    self.__apply_broker_values__(close_transactions, Action.CLOSE)
                    self.__add_tags__(close_transactions, strategy.get_short_indicator_names)
                    self.transactions = self.transactions.append(close_transactions, ignore_index=True)
                    self.update_positions(close_transactions, Direction.LONG)
                    self.update_account(close_transactions)

    def update_equity_curve(self, date):
        if self.equity_curve.empty:
            index = pd.to_datetime(date) - datetime.timedelta(days=1)
            self.equity_curve.loc[index] = pd.Series()
            self.equity_curve.loc[index, EquityCurveKey.EQUITY.value] = self.account.starting_balance
            self.equity_curve.loc[index, EquityCurveKey.CASH.value] = self.account.starting_balance
            self.equity_curve = self.equity_curve.fillna(0)
            print(index.strftime(config.DATE_FORMAT),
                  '{:>18.4f}'.format(self.equity_curve.loc[index][EquityCurveKey.EQUITY.value]),
                  '{:>18.4f}'.format(self.equity_curve.loc[index][EquityCurveKey.CASH.value]),
                  '{:>13.4f}'.format(self.equity_curve.loc[index][EquityCurveKey.DRAWDOWN_PERCENT.value]))

        self.equity_curve.loc[date] = pd.Series()
        self.equity_curve.loc[date, EquityCurveKey.EQUITY.value] = self.account.equity
        self.equity_curve.loc[date, EquityCurveKey.CASH.value] = self.account.cash
        self.equity_curve[EquityCurveKey.DRAWDOWN.value] = self.equity_curve[EquityCurveKey.EQUITY.value].expanding(1).apply(
                                                            lambda d: -(d.max()-d[-1]))
        self.equity_curve[EquityCurveKey.DRAWDOWN_PERCENT.value] = self.equity_curve[EquityCurveKey.EQUITY.value].expanding(1).apply(
                                                                    lambda d: -(100 * (d.max()-d[-1]) / d.max()))
        self.equity_curve = utils.round_df(self.equity_curve)

    def update(self, date, symbols):
        if self.equity_curve.empty and os.path.exists(self.dir_path / self.name):
            self.load(self.dir_path)

        if self.equity_curve.empty or date > self.equity_curve.index.values[-1]:
            super().update(date, symbols)
            self.update_positions(None, None, date)
            self.update_account(pd.DataFrame(columns=TRANSACTION_COLUMNS))
            self.update_equity_curve(date)
            self.save(self.dir_path)
            print(pd.to_datetime(date).strftime(config.DATE_FORMAT),
                  '{:>18.4f}'.format(self.get_equity(date)),
                  '{:>18.4f}'.format(self.get_cash(date)),
                  '{:>13.4f}'.format(self.get_drawdown_percent(date)))

    def save(self, dir_path):
        save_dir_path = dir_path / self.name
        utils.makedirs(save_dir_path)
        self.equity_curve.to_pickle(save_dir_path / self.EQUITY_CURVE_FILENAME)
        self.positions.to_pickle(save_dir_path / self.POSITIONS_FILENAME)
        self.transactions.to_pickle(save_dir_path / self.TRANSACTIONS_FILENAME)

    def load(self, dir_path):
        save_dir_path = dir_path / self.name
        print('Loading portfolio data from {}...'.format(save_dir_path))
        self.equity_curve = pd.read_pickle(save_dir_path / self.EQUITY_CURVE_FILENAME)
        self.positions = pd.read_pickle(save_dir_path / self.POSITIONS_FILENAME)
        self.transactions = pd.read_pickle(save_dir_path / self.TRANSACTIONS_FILENAME)
        self.account.equity = self.equity_curve[EquityCurveKey.EQUITY.value].values[-1]
        self.account.cash = self.equity_curve[EquityCurveKey.CASH.value].values[-1]
        self.account.starting_balance = self.equity_curve[EquityCurveKey.EQUITY.value].values[0]

    def get_positions(self):
        return self.positions

    def get_transactions(self):
        return self.transactions

    def get_equity(self, date):
        return self.equity_curve.loc[date][EquityCurveKey.EQUITY.value]

    def get_cash(self, date):
        return self.equity_curve.loc[date][EquityCurveKey.CASH.value]

    def get_drawdown(self, date):
        return self.equity_curve.loc[date][EquityCurveKey.DRAWDOWN.value]

    def get_drawdown_percent(self, date):
        return self.equity_curve.loc[date][EquityCurveKey.DRAWDOWN_PERCENT.value]


def create_equity_chart(df_equity_curve, fpath=None):
    items = df_equity_curve.apply(lambda d: EquityCurveItem(*[d[_.value] for _ in EquityCurveKey]), axis=1)
    chart_data = EquityCurveChart(indices=df_equity_curve.index.values,
                                  equity_curve_items=items,
                                  index_labels=[pd.to_datetime(_).strftime(config.DATE_FORMAT) for _ in df_equity_curve.index.values])
    charting_equity_curve.create(chart_data, fpath=fpath)


if __name__ == '__main__':
    INDICATORS_PATH = config.TEMP_PATH / 'indicators'
    HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'

    pse_market = pkl_to_market('PSE', HISTORICAL_DATA_PATH)
    strategies = [DonchianChannel(PickleIndicatorFactory(INDICATORS_PATH, market=pse_market))]
    portfolio = DataFramePortfolio(account=Account(1000000), dir_path=config.RESOURCES_PATH, indicators_dir_path=INDICATORS_PATH,
                                   market=pse_market, position_sizing=EquityPercentage(market=pse_market),
                                   broker=COLFinancial(), strategies=strategies,
                                   name='Portfolio')
    default = DataFrameBacktester(portfolio)
    equity_curve = default.run(pse_market, start=pd.to_datetime('2015-01-01'))
    equity_curve = utils.round_df(equity_curve, 2)
    print(equity_curve)
    create_equity_chart(equity_curve)
    #portfolio.save_charts(config.RESOURCES_PATH / '{}_charts'.format(portfolio.name))
