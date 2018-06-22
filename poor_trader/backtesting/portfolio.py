import os

import pandas as pd

from poor_trader import config
from poor_trader.backtesting.backtester import TransactionService, PositionService
from poor_trader.backtesting.entity import Portfolio, Account, Broker, PositionSizing, EquityCurve, Position
from poor_trader.market import Market
from poor_trader.screening.entity import Direction


class DefaultPortfolio(Portfolio):

    def __init__(self, account: Account, market: Market, broker: Broker, position_sizing: PositionSizing,
                 equity_curve: EquityCurve, strategies=list(), name=None, save_dir_path=None):
        super().__init__(account=account, equity_curve=equity_curve, name=name or self.__class__.__name__, strategies=strategies)
        self.market = market
        self.broker = broker
        self.position_sizing = position_sizing
        self.transaction_service = TransactionService()
        self.position_service = PositionService()
        self.save_dir_path = save_dir_path or config.generate_backtesting_results_dir_path()
        print('!!!Saving backtest results to ' + self.save_dir_path)

    def update_account_on_close(self, exit_value):
        self.account.cash = self.account.cash + exit_value
        self.account.buying_power = self.account.cash

    def close(self, position: Position, tags: str):
        self.update_account_on_close(position.value)
        self.transaction_service.close(position.exit_date, position.symbol, position.price, position.shares, position.value, tags)
        self.position_service.save(position)

    def close_positions(self, date, symbols):
        for position in self.get_positions():
            for strategy in self.strategies:
                if strategy.exit_condition(date=date, symbol=position.symbol, market=self.market,
                                           entry_date=position.entry_date, direction=position.direction):
                    position.exit_date = date
                    self.close(position, self.__get_tags__(position.direction, position.exit_date, position.symbol,
                                                           position.entry_date))
                    break

    def update_account_on_open(self, entry_value=0.0, exit_value=0.0):
        self.account.cash = self.account.cash - entry_value
        self.account.buying_power = self.account.cash
        self.account.equity = self.account.cash + exit_value

    def open(self, date, symbol, tags):
        price = self.market.get_close(date, symbol)
        shares = self.position_sizing.calculate_shares(date=date, symbol=symbol, account=self.account)
        if shares > 0:
            value = self.broker.calculate_buy_value(price=price, shares=shares)
            sell_value = self.broker.calculate_sell_value(price=price, shares=shares)
            if value <= self.account.buying_power:
                self.update_account_on_open(entry_value=value, exit_value=sell_value + self.position_service.get_open_values())
                self.transaction_service.open(date, symbol, price, shares, value, tags)
                position = Position(date, None, Direction.LONG, symbol, shares, price, value)
                self.position_service.save(position)

    def open_positions(self, date, symbols):
        if self.account.buying_power <= 0:
            pass
        open_symbols = self.position_service.get_open_symbols()
        remaining_symbols = [_ for _ in symbols if _ not in open_symbols]
        for symbol in remaining_symbols:
            for strategy in self.strategies:
                if strategy.entry_condition(date=date, symbol=symbol, market=self.market, direction=Direction.LONG):
                    self.open(date, symbol, self.__get_tags__(Direction.LONG, date, symbol))
                    break

    def update_open_positions_values(self, date):
        for position in self.position_service.get_open_positions():
            price = self.market.get_close(date=date, symbol=position.symbol)
            try:
                if not pd.isnull(price):
                    position.price = price
                    position.value = self.broker.calculate_sell_value(price=price, shares=position.shares)
                    self.position_service.save(position)
            except ValueError:
                # print('No price update for {} on {}.'.format(position.symbol, pd.to_datetime(date).strftime(config.DATETIME_FORMAT)))
                pass

    def update(self, date, symbols):
        self.close_positions(date=date, symbols=symbols)
        self.open_positions(date=date, symbols=symbols)
        self.update_open_positions_values(date)
        self.update_account_on_open(exit_value=self.position_service.get_open_values())
        self.equity_curve.update(date, self.account)
        print(pd.to_datetime(date).strftime(config.DATETIME_FORMAT),
              '{:>18.4f}'.format(self.equity_curve.get_equity(date)),
              '{:>18.4f}'.format(self.equity_curve.get_cash(date)),
              '{:>13.4f}'.format(self.equity_curve.get_drawdown_percent(date)))
        self.save(self.save_dir_path)

    def get_positions(self):
        return self.position_service.get_open_positions()

    def get_transactions(self):
        return self.transaction_service.get_transactions()

    def save(self, dir_path):
        save_dir_path = dir_path / self.name
        self.equity_curve.save_to_file(save_dir_path)
        self.position_service.save_to_file(save_dir_path)
        self.transaction_service.save_to_file(save_dir_path)


if __name__ == '__main__':
    from poor_trader.market import pkl_to_market
    from poor_trader.backtesting.backtester import DataFrameBacktester
    from poor_trader.backtesting.broker import COLFinancial
    from poor_trader.backtesting.equity_curve import DefaultEquityCurve
    from poor_trader.backtesting.position_sizing import EquityPercentage
    from poor_trader.screening.indicator import PickleIndicatorFactory
    from poor_trader.screening.strategy import DonchianChannel, ATRChannelBreakout

    investa_symbols = ['ALI', 'AC',    'MBT', 'SM',    'SMPH', 'JFC',   'URC',   'MPI', 'ICT',  'BLOOM',
                       'BPI', 'NOW',   'TEL', 'GTCAP', 'VITA', 'JGS',   'SECB',  'MER', 'AGI',  'HOUSE',
                       'AEV', 'PGOLD', 'DMC', 'MEG',   'LTG',  'GLO',   'MWIDE', 'MRC', 'RLC',  'MAC',
                       'SCC', 'PXP',   'AP',  'VLL',   'FB',   'EAGLE', 'WLCON', 'LR',  'SMC',  'RWM',
                       'DNL', 'MRP',   'CHP', 'IMI',   'FNI',  'EW',    'VUL',   'CLC', 'PCOR', 'BRN',
                       'LPZ', 'ANI',   'FLI', 'DD',    'PRMX', 'ATN',   'APX',   'CPM', 'TUGS', 'PIZZA',
                       'X',   'POPI',  'CPG', 'NIKL',  'ION']

    INDICATORS_PATH = config.TEMP_PATH / 'indicators'
    HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'

    pse_market = pkl_to_market('PSE', HISTORICAL_DATA_PATH, symbols=investa_symbols)
    strategies = [DonchianChannel(PickleIndicatorFactory(INDICATORS_PATH, market=pse_market), fast=100, slow=120),
                  ATRChannelBreakout(PickleIndicatorFactory(INDICATORS_PATH, market=pse_market), fast=100, slow=120)]

    colport = DefaultPortfolio(account=Account(1000000),
                               market=pse_market,
                               broker=COLFinancial(),
                               position_sizing=EquityPercentage(pse_market),
                               equity_curve=DefaultEquityCurve(),
                               strategies=strategies,
                               name='test3')
    default = DataFrameBacktester(colport)
    ec = default.run(pse_market, start=pd.to_datetime('2017-08-20'), end=pd.to_datetime('2017-11-23'))
