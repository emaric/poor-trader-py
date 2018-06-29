import os
import shutil
import unittest
import pandas as pd

from poor_trader import market, config
from poor_trader.screening import indicator, strategy
from tests import test_indicator


class TestStrategy(unittest.TestCase):
    def setUp(self):
        self.tearDown()
        self.market = market.csv_to_market('TestMarket', test_indicator.INTRADAY_HISTORICAL_DATA_PATH)
        self.indicator_factory = indicator.DefaultIndicatorFactory(test_indicator.TEMP_INDICATORS_PATH, self.market)

    def tearDown(self):
        if os.path.exists(config.TEST_TEMP_PATH):
            shutil.rmtree(config.TEST_TEMP_PATH)

    def run_assertions(self, _strategy):
        self.assertTrue(len(_strategy.indicators) > 0)
        for date in self.market.get_dates():
            long = [symbol for symbol in self.market.get_symbols(date) if _strategy.is_long(date, symbol)]
            short = [symbol for symbol in self.market.get_symbols(date) if _strategy.is_short(date, symbol)]
            if len(long) > 0 or len(short) > 0:
                print(pd.to_datetime(date).strftime(config.DATETIME_FORMAT), 'LONG:', long, 'SHORT:', short)
            if len(long) > 0:
                for symbol in long:
                    self.assertEqual([_.name for _ in _strategy.indicators],
                                     _strategy.get_long_indicator_names(date, symbol), msg=symbol)
            if len(short) > 0:
                for symbol in short:
                    self.assertEqual([_.name for _ in _strategy.indicators],
                                     _strategy.get_short_indicator_names(date, symbol), msg=symbol)

    def test_atr_channel_breakout_strategy(self):
        atr_channel_breakout = strategy.ATRChannelBreakout(self.indicator_factory, sma=5, fast=5, slow=10)
        self.run_assertions(atr_channel_breakout)

    def test_donchian_channel_strategy(self):
        dc = strategy.DonchianChannel(self.indicator_factory, high=10, low=10, fast=5, slow=10)
        self.run_assertions(dc)

    def test_trend_strength_strategy(self):
        ts = strategy.TrendStrength(self.indicator_factory, start=5, end=10, step=1, fast=5, slow=10)
        self.run_assertions(ts)


if __name__ == '__main__':
    unittest.main()
