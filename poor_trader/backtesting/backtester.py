from enum import Enum

import pandas as pd

from poor_trader import config, utils
from poor_trader.backtesting.broker import COLFinancial
from poor_trader.backtesting.entity import Backtester, Portfolio, Account, PositionSizing, Broker, Action
from poor_trader.backtesting.position_sizing import EquityPercentage
from poor_trader.market import Market, pkl_to_market
from poor_trader.screening.entity import Direction
from poor_trader.screening.indicator import PickleIndicatorFactory
from poor_trader.screening.strategy import Strategy


class EquityCurveEnum(Enum):
    EQUITY = 'Equity'
    CASH = 'Cash'
    DRAWDOWN = 'Drawdown'
    DRAWDOWN_PERCENT = 'DrawdownPercent'


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


EQUITY_CURVE_COLUMNS = [_.value for _ in EquityCurveEnum]
TRANSACTION_COLUMNS = [_.value for _ in TransactionEnum]
POSITION_COLUMNS = [_.value for _ in PositionEnum]


class DataFrameBacktester(Backtester):
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def run(self, market: Market, start=None, end=None):
        df = pd.DataFrame(columns=EQUITY_CURVE_COLUMNS)
        for date in market.get_dates():
            symbols = market.get_symbols(date)
            self.portfolio.update(date, symbols)
            df.loc[date] = pd.Series()
            df.loc[date][EquityCurveEnum.EQUITY.value] = self.portfolio.get_equity(date)
            df.loc[date][EquityCurveEnum.CASH.value] = self.portfolio.get_cash(date)
            df.loc[date][EquityCurveEnum.DRAWDOWN.value] = self.portfolio.get_drawdown(date)
            df.loc[date][EquityCurveEnum.DRAWDOWN_PERCENT.value] = self.portfolio.get_drawdown_percent(date)
        return utils.round_df(df)


class DataFramePortfolio(Portfolio):
    def __init__(self, account: Account,
                 indicators_dir_path,
                 market: Market,
                 position_sizing: PositionSizing,
                 broker: Broker,
                 name=None, strategies=list()):
        super().__init__(account, name, strategies)
        self.indicators_dir_path = indicators_dir_path
        self.market = market
        self.position_sizing = position_sizing
        self.broker = broker
        self.strategies = self.__init_strategies__()
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

    def __add_long_tags__(self, open_transactions, strategy):
        if not open_transactions.empty:
            open_transactions[TransactionEnum.TAGS.value] = open_transactions.apply(
                lambda t: ' '.join(strategy.get_long_indicator_names(t[TransactionEnum.DATE.value],
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
                lambda p: self.market.get_close(date, p[PositionEnum.SYMBOL.value]), axis=1)
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
            for strategy in self.strategies:
                long_symbols = [_ for _ in symbols if strategy.is_long(date, _)]
                open_transactions = self.open(date, long_symbols)
                self.__apply_open_position_sizing__(open_transactions)
                self.__apply_boardlot__(open_transactions)
                self.__apply_broker_values__(open_transactions, Action.OPEN)
                while self.account.cash < open_transactions[TransactionEnum.VALUE.value].sum():
                    open_transactions = open_transactions[open_transactions[TransactionEnum.VALUE.value] > open_transactions[TransactionEnum.VALUE.value].min()]
                if not open_transactions.empty:
                    self.__add_long_tags__(open_transactions, strategy)
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
            close_transactions = self.close(date, open_symbols)
            if not close_transactions.empty:
                self.__apply_close_position_sizing__(close_transactions)
                self.__apply_broker_values__(close_transactions, Action.CLOSE)
                self.transactions = self.transactions.append(close_transactions, ignore_index=True)
                self.update_positions(close_transactions, Direction.LONG)
                self.update_account(close_transactions)

    def update_equity_curve(self, date):
        self.equity_curve.loc[date] = pd.Series()
        self.equity_curve.loc[date, EquityCurveEnum.EQUITY.value] = self.account.equity
        self.equity_curve.loc[date, EquityCurveEnum.CASH.value] = self.account.cash
        self.equity_curve[EquityCurveEnum.DRAWDOWN.value] = self.equity_curve[EquityCurveEnum.EQUITY.value].expanding(1).apply(
            lambda d: -(d.max()-d[-1]))
        self.equity_curve[EquityCurveEnum.DRAWDOWN_PERCENT.value] = self.equity_curve[EquityCurveEnum.EQUITY.value].expanding(1).apply(
            lambda d: -(100 * (d.max()-d[-1]) / d.max()))
        self.equity_curve = utils.round_df(self.equity_curve)

    def update(self, date, symbols):
        super().update(date, symbols)
        self.update_positions(None, None, date)
        self.update_account(pd.DataFrame(columns=TRANSACTION_COLUMNS))
        self.update_equity_curve(date)
        print(pd.to_datetime(date).strftime(config.DATE_FORMAT),
              '{:>18.4f}'.format(self.get_equity(date)),
              '{:>18.4f}'.format(self.get_cash(date)),
              '{:>13.4f}'.format(self.get_drawdown_percent(date)))

    def get_positions(self):
        return self.positions

    def get_transactions(self):
        return self.transactions

    def get_equity(self, date):
        return self.equity_curve.loc[date][EquityCurveEnum.EQUITY.value]

    def get_cash(self, date):
        return self.equity_curve.loc[date][EquityCurveEnum.CASH.value]

    def get_drawdown(self, date):
        return self.equity_curve.loc[date][EquityCurveEnum.DRAWDOWN.value]

    def get_drawdown_percent(self, date):
        return self.equity_curve.loc[date][EquityCurveEnum.DRAWDOWN_PERCENT.value]


if __name__ == '__main__':
    INDICATORS_PATH = config.TEMP_PATH / 'indicators'
    HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'
    print('INDICATOR_PATH', INDICATORS_PATH)

    pse_market = pkl_to_market('PSE', HISTORICAL_DATA_PATH)

    account = Account(100000)
    portfolio = DataFramePortfolio(account=account,
                                   indicators_dir_path=INDICATORS_PATH,
                                   market=pse_market,
                                   position_sizing=EquityPercentage(market=pse_market),
                                   broker=COLFinancial(),
                                   name='Portfolio')
    default = DataFrameBacktester(portfolio)
    equity_curve = default.run(pse_market)
    print(equity_curve)
