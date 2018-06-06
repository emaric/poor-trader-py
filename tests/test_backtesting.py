import unittest

import pandas as pd
from poor_trader.backtesting.backtester import DataFramePortfolio, DataFrameBacktester
from poor_trader.backtesting.broker import COLFinancial
from poor_trader.backtesting.entity import Account
from poor_trader.backtesting.position_sizing import EquityPercentage
from poor_trader.market import csv_to_market
from poor_trader.screening.indicator import PickleIndicatorFactory
from poor_trader.screening.strategy import ATRChannelBreakout
from tests import test_indicator


class TestBacktesting(unittest.TestCase):
    def setUp(self):
        self.market = csv_to_market('TestMarket', test_indicator.INTRADAY_HISTORICAL_DATA_PATH)
        self.account = Account(100000)

        class TestPortfolio(DataFramePortfolio):
            def __init_strategies__(self):
                indicator_factory = PickleIndicatorFactory(test_indicator.TEMP_INDICATORS_PATH, self.market)
                atr_channel_breakout = ATRChannelBreakout(indicator_factory, sma=10, fast=5, slow=10)
                return [atr_channel_breakout]

        self.portfolio = TestPortfolio(account=self.account,
                                       indicators_dir_path=test_indicator.TEMP_INDICATORS_PATH,
                                       market=self.market,
                                       position_sizing=EquityPercentage(market=self.market),
                                       broker=COLFinancial())

    def test_backtester(self):
        backtester = DataFrameBacktester(self.portfolio)
        equity_curve = backtester.run(self.market)
        print(equity_curve)
        self.assertTrue(pd.Index.equals(equity_curve.index, self.market.__df_historical_data__.index))


if __name__ == '__main__':
    unittest.main()
