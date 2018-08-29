import pandas as pd

from poor_trader import config
from poor_trader.charting import transactions as charting_transactions
from poor_trader.charting import equity_curve as charting_equity_curve
from poor_trader.backtesting.backtester import DefaultBacktester
from poor_trader.backtesting.broker import PSEDefaultBroker
from poor_trader.backtesting.entity import Account
from poor_trader.backtesting.equity_curve import DefaultEquityCurve
from poor_trader.backtesting.portfolio import DefaultPortfolio
from poor_trader.backtesting.position_sizing import FixedFractional, ATRBased, RiskedBased
from poor_trader.market import pkl_to_market
from poor_trader.screening import strategy
from poor_trader.screening.indicator import DefaultIndicatorFactory

INDICATORS_PATH = config.TEMP_PATH / 'indicators'
HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'

symbols = ['ALI', 'AC',    'MBT', 'SM',    'SMPH', 'JFC',   'URC',   'MPI', 'ICT',  'BLOOM',
           'BPI', 'NOW',   'TEL', 'GTCAP', 'VITA', 'JGS',   'SECB',  'MER', 'AGI',  'HOUSE',
           'AEV', 'PGOLD', 'DMC', 'MEG',   'LTG',  'GLO',   'MWIDE', 'MRC', 'RLC',  'MAC',
           'SCC', 'PXP',   'AP',  'VLL',   'FB',   'EAGLE', 'WLCON', 'LR',  'SMC',  'RWM',
           'DNL', 'MRP',   'CHP', 'IMI',   'FNI',  'EW',    'VUL',   'CLC', 'PCOR', 'BRN',
           'LPZ', 'ANI',   'FLI', 'DD',    'PRMX', 'ATN',   'APX',   'CPM', 'TUGS', 'PIZZA',
           'X',   'POPI',  'CPG', 'NIKL',  'ION']

most_active = ['MBT', 'ALI', 'BDO', 'AC', 'SM', 'BPI', 'SECB', 'ICT', 'JFC',
               'SMPH', 'MER', 'MWIDE', 'GTCAP', 'NOW', 'AEV', 'WIN', 'AGI',
               'IRC', 'JGS', 'BLOOM', 'MPI', 'ISM', 'TEL', 'MEG', 'URC', 'GLO',
               'DMC', 'SEVN', 'VLL', 'WLCON', 'MHC', 'ECP', 'LTG', 'RLC', 'PHES',
               'VUL', 'TECH', 'AP', 'X', 'FLI', 'ABG', 'IMI', 'H2O', 'DNL', 'VITA',
               'MRC', 'EMP', 'ANI', 'ATN', 'NIKL', 'CLC', 'TBGI', 'PRMX', 'MAC',
               'ORE', 'CEB', 'SCC', 'SHLPH', 'ION', 'SMC', 'RRHI', 'MWP', 'ABSP',
               'FNI', 'DD', 'PCOR', 'MRP', 'PGOLD', 'EAGLE', 'FPH', 'APX', 'UBP',
               'SSI', 'TUGS', 'ABS', 'RWM', 'WPI', 'STR', 'COSCO', 'MAH', 'ATNB',
               'PXP', 'PIP', 'IDC', 'IS', 'FGEN', 'JAS', 'HVN', 'CHIB', 'CHP', 'AT']

symbols = [_ for _ in symbols if _ in most_active]

starting_balance = 100000

broker = PSEDefaultBroker()

market = pkl_to_market('PSE', HISTORICAL_DATA_PATH, symbols=symbols)

factory = DefaultIndicatorFactory(INDICATORS_PATH, market)

position_sizing = FixedFractional(market)

# position_sizing = ATRBased(market, factory)

# position_sizing = RiskedBased(market)

save_dir_path = config.USER_APP_DIR_PATH / 'investa'

# dc = strategy.DonchianChannel(factory, 50, 50, fast=40, slow=60)
dc = strategy.DonchianChannel(factory)
atr = strategy.ATRChannelBreakout(factory, sma=20, fast=40, slow=100)
ts = strategy.TrendStrength(factory, fast=10, slow=60)
stop_price = strategy.StopPriceStrategy()

dc_portfolio = DefaultPortfolio(account=Account(starting_balance),
                                market=market,
                                broker=broker,
                                position_sizing=position_sizing,
                                equity_curve=DefaultEquityCurve(),
                                strategies=[dc],
                                name='DonchianChannel_Portfolio',
                                save_dir_path=save_dir_path)

atr_portfolio = DefaultPortfolio(account=Account(starting_balance),
                                 market=market,
                                 broker=broker,
                                 position_sizing=position_sizing,
                                 equity_curve=DefaultEquityCurve(),
                                 strategies=[atr],
                                 name='ATRChannelBreakout_Portfolio',
                                 save_dir_path=save_dir_path)

ts_portfolio = DefaultPortfolio(account=Account(starting_balance),
                                market=market,
                                broker=broker,
                                position_sizing=position_sizing,
                                equity_curve=DefaultEquityCurve(),
                                strategies=[ts],
                                name='TrendStrength_Portfolio',
                                save_dir_path=save_dir_path)

default_portfolio = DefaultPortfolio(account=Account(starting_balance),
                                     market=market,
                                     broker=broker,
                                     position_sizing=position_sizing,
                                     equity_curve=DefaultEquityCurve(),
                                     strategies=[dc, atr, ts],
                                     name='DefaultPorfolio',
                                     save_dir_path=save_dir_path)

start = pd.to_datetime('2016-08-24')
end = pd.to_datetime('2018-08-24')


def create_chart(portfolio: DefaultPortfolio):
    csv_path = (portfolio.save_dir_path / portfolio.name) / 'transactions.csv'
    output_path = csv_path.parent / 'charts'
    # TODO: charting_equity_curve.csv_to_chart()
    charting_transactions.csv_to_chart(market, csv_path, output_path,
                                       indicator_factory=factory,
                                       indicator_runner_factory=factory.runner_factory)


if __name__ == '__main__':
    import shutil
    import os
    if os.path.exists(save_dir_path):
        shutil.rmtree(save_dir_path)

    portfolios = [dc_portfolio, atr_portfolio, ts_portfolio, default_portfolio]
    for p in portfolios:
        p.print_details()
        DefaultBacktester(p).run(market, start, end)
        create_chart(p)
