import os
import shutil
import unittest

import pandas as pd

from poor_trader import config
from poor_trader.backtesting.backtester import DataFrameBacktester
from poor_trader.backtesting.broker import COLFinancial
from poor_trader.backtesting.entity import Account
from poor_trader.backtesting.equity_curve import DefaultEquityCurve
from poor_trader.backtesting.portfolio.colfinancial import DefaultPortfolio
from poor_trader.backtesting.position_sizing import EquityPercentage
from poor_trader.market import csv_to_market
from poor_trader.screening.indicator import PickleIndicatorFactory
from poor_trader.screening.strategy import ATRChannelBreakout
from tests import test_indicator


class TestBacktesting(unittest.TestCase):
    def setUp(self):
        self.tearDown()
        self.market = csv_to_market('TestMarket', test_indicator.INTRADAY_HISTORICAL_DATA_PATH)
        self.account = Account(100000)

        indicator_factory = PickleIndicatorFactory(test_indicator.TEMP_INDICATORS_PATH, self.market)
        atr_channel_breakout = ATRChannelBreakout(indicator_factory, sma=10, fast=5, slow=10)

        self.portfolio = DefaultPortfolio(account=self.account,
                                          market=self.market,
                                          position_sizing=EquityPercentage(market=self.market),
                                          broker=COLFinancial(),
                                          equity_curve=DefaultEquityCurve(),
                                          strategies=[atr_channel_breakout])

    def tearDown(self):
        if os.path.exists(config.TEST_TEMP_PATH):
            shutil.rmtree(config.TEST_TEMP_PATH)

    def test_backtester(self):
        backtester = DataFrameBacktester(self.portfolio)
        equity_curve = backtester.run(self.market)
        print(equity_curve.get_equity())
        self.assertTrue(pd.Index.equals(equity_curve.get_equity()[1:].index, self.market.__df_historical_data__.index))


if __name__ == '__main__':
    unittest.main()
