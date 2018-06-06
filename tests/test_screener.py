import unittest

from poor_trader import market
from poor_trader.screening.screener import DataFrameScreener
from tests import test_indicator


class TestScreening(unittest.TestCase):
    def setUp(self):
        self.market = market.csv_to_market('TestMarket', test_indicator.INTRADAY_HISTORICAL_DATA_PATH)

    def test_screener(self):
        screener = DataFrameScreener(self.market, test_indicator.TEMP_INDICATORS_PATH)
        df_long, df_short = screener.scan()
        screener.print('LONG', df_long)

        indicators = screener.create_indicators()
        self.assertTrue(len(indicators) > 0)
        for i in indicators:
            self.assertTrue(i.name in df_long.columns)


if __name__ == '__main__':
    unittest.main()
