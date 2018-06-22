import os
import shutil
import unittest

import pandas as pd

from poor_trader import config
from poor_trader.market import csv_to_market
from poor_trader.screening.indicator import PickleIndicatorRunnerFactory, IndicatorRunner, PickleIndicatorFactory
from poor_trader.screening.screener import DataFrameScreener

INDICATORS_PATH = config.TEST_TEMP_PATH / 'indicators'
HISTORICAL_DATA_PATH = config.TEST_RESOURCES_PATH / 'intraday_historical_data.csv'


class TestScreening(unittest.TestCase):
    def setUp(self):
        self.tearDown()
        self.market = csv_to_market('TestMarket', HISTORICAL_DATA_PATH)

    def tearDown(self):
        if os.path.exists(INDICATORS_PATH):
            shutil.rmtree(INDICATORS_PATH)

    def test_runner_factory(self):
        indicator_runner_factory = PickleIndicatorRunnerFactory(INDICATORS_PATH)
        indicator_classes = IndicatorRunner.__subclasses__()
        for indicator_class in indicator_classes:
            indicator_instance = indicator_runner_factory.create(indicator_class)
            for symbol in self.market.get_symbols():
                df_quotes = self.market.get_quotes(symbol=symbol)
                df = indicator_instance.run(symbol, df_quotes)
                self.assertTrue(pd.Index.equals(df.index, df_quotes.index),
                                msg=symbol)

    def test_factory(self):
        indicator_factory = PickleIndicatorFactory(INDICATORS_PATH, market=self.market)
        indicator_classes = IndicatorRunner.__subclasses__()
        for indicator_class in indicator_classes:
            indicator_instance = indicator_factory.create(indicator_class)
            for symbol in self.market.get_symbols():
                print('test_factory:', symbol, 'indicator_instance:', indicator_instance.name)
                if symbol == '2GO' and indicator_instance.name == 'ema_Close_10':
                    print('test')
                df_quotes = self.market.get_quotes(symbol=symbol)
                indices = indicator_instance.get_indices(symbol=symbol)
                self.assertSetEqual(set(df_quotes.index.values), set(indices), symbol)

    def test_screener(self):
        screener = DataFrameScreener(self.market, INDICATORS_PATH)
        df_long, df_short = screener.scan()
        screener.print('LONG', df_long)

        indicators = screener.create_indicators()
        self.assertTrue(len(indicators) > 0)
        for i in indicators:
            self.assertTrue(i.name in df_long.columns)


if __name__ == '__main__':
    unittest.main()
