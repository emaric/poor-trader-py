import os
import shutil
import unittest

import pandas as pd

from poor_trader import config
from poor_trader.backtesting.backtester import DefaultBacktester
from poor_trader.backtesting.broker import PSEDefaultBroker
from poor_trader.backtesting.entity import Account
from poor_trader.backtesting.equity_curve import DefaultEquityCurve
from poor_trader.backtesting.portfolio import DefaultPortfolio
from poor_trader.backtesting.position_sizing import FixedFractional
from poor_trader.market import csv_to_market
from poor_trader.screening.indicator import DefaultIndicatorFactory
from poor_trader.screening.strategy import ATRChannelBreakout, TrendStrength
from tests import test_indicator


class TestBacktesting(unittest.TestCase):
    def setUp(self):
        self.portfolio = None
        self.tearDown()
        self.market = csv_to_market('TestMarket', test_indicator.INTRADAY_HISTORICAL_DATA_PATH)
        self.account = Account(100000)

        indicator_factory = DefaultIndicatorFactory(test_indicator.TEMP_INDICATORS_PATH, self.market)
        atr_channel_breakout = ATRChannelBreakout(indicator_factory, sma=10, fast=5, slow=10)
        trend_strength = TrendStrength(indicator_factory, start=5, end=10, step=1, fast=5, slow=10)

        self.portfolio = DefaultPortfolio(account=self.account,
                                          market=self.market,
                                          position_sizing=FixedFractional(market=self.market),
                                          broker=PSEDefaultBroker(),
                                          equity_curve=DefaultEquityCurve(),
                                          strategies=[atr_channel_breakout, trend_strength])

    def tearDown(self):
        if os.path.exists(config.TEST_TEMP_PATH):
            shutil.rmtree(config.TEST_TEMP_PATH)

        if self.portfolio and os.path.exists(self.portfolio.save_dir_path):
            shutil.rmtree(self.portfolio.save_dir_path)

    def test_backtester(self):
        backtester = DefaultBacktester(self.portfolio)
        equity_curve = backtester.run(self.market)
        print(equity_curve.get_equity())
        self.assertTrue(pd.Index.equals(equity_curve.get_equity()[1:].index, self.market.__df_historical_data__.index))


if __name__ == '__main__':
    unittest.main()
