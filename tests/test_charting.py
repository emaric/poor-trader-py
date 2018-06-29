import os
import shutil
import unittest

from poor_trader import config
from poor_trader.charting import equity_curve, transactions
from poor_trader.market import csv_to_market
from poor_trader.screening.indicator import DefaultIndicatorFactory
from tests import test_indicator

BACKTEST_RESULT_PATH = config.TEST_RESOURCES_PATH / 'backtest_result'

EQUITY_CURVE_PATH = BACKTEST_RESULT_PATH / config.EQUITY_CURVE_FILENAME

TRANSACTIONS_PATH = BACKTEST_RESULT_PATH / config.TRANSACTIONS_FILENAME

TEMP_INDICATORS_PATH = config.TEST_TEMP_PATH / 'indicators'


class TestCharting(unittest.TestCase):
    def setUp(self):
        self.tearDown()
        self.market = csv_to_market('TestMarket', test_indicator.INTRADAY_HISTORICAL_DATA_PATH)

    def tearDown(self):
        if os.path.exists(config.TEST_TEMP_PATH):
            shutil.rmtree(config.TEST_TEMP_PATH)

    def test_equity_curve(self):
        equity_curve.csv_to_chart(EQUITY_CURVE_PATH)

    def test_transactions(self):
        factory = DefaultIndicatorFactory(TEMP_INDICATORS_PATH, self.market)
        transactions.csv_to_chart(self.market, TRANSACTIONS_PATH,
                                  indicator_factory=factory,
                                  indicator_runner_factory=factory.runner_factory)


if __name__ == '__main__':
    unittest.main()
