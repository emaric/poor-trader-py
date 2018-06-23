import unittest

from poor_trader import config
from poor_trader.charting import equity_curve, transactions
from poor_trader.market import csv_to_market
from tests import test_indicator

BACKTEST_RESULT_PATH = config.TEST_RESOURCES_PATH / 'backtest_result'

EQUITY_CURVE_PATH = BACKTEST_RESULT_PATH / config.EQUITY_CURVE_FILENAME

TRANSACTIONS_PATH = BACKTEST_RESULT_PATH / config.TRANSACTIONS_FILENAME


class TestCharting(unittest.TestCase):
    def setUp(self):
        self.market = csv_to_market('TestMarket', test_indicator.INTRADAY_HISTORICAL_DATA_PATH)

    def test_equity_curve(self):
        equity_curve.csv_to_chart(EQUITY_CURVE_PATH)

    def test_transactions(self):
        transactions.csv_to_chart(self.market, TRANSACTIONS_PATH)
        self.fail('TODO: Add indicators based on the transaction tags.')


if __name__ == '__main__':
    unittest.main()
