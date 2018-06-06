import unittest

import pandas as pd
from pandas.util.testing import assert_frame_equal

from poor_trader import market, config

HISTORICAL_DATA_CSV_PATH = config.TEST_RESOURCES_PATH / 'historical_data.csv'


def trim_symbol_from_columns(symbol, df):
    _df = df
    _df.columns = [_.replace('{}_'.format(symbol), '') for _ in _df.columns]
    return _df


class TestMarket(unittest.TestCase):
    def setUp(self):
        self.df_historical_data = pd.read_csv(HISTORICAL_DATA_CSV_PATH, parse_dates=True, index_col=0)
        self.market = market.csv_to_market('TestMarket', HISTORICAL_DATA_CSV_PATH)
        self.symbol = self.market.get_symbols()[0]
        self.date = self.market.get_dates()[0]

    def test_get_dates(self):
        dates = self.market.get_dates()
        self.assertEqual(5, len(dates))

    def test_get_dates_symbols(self):
        dates = self.market.get_dates(symbols=['2GO', 'ABA', 'ABG'])
        df = self.df_historical_data
        drop_columns_with_na = df.filter(like='Date').dropna(axis=1)
        retain_columns_with_na = df.filter(like='Date').drop(columns=drop_columns_with_na.columns)
        symbols = [_[:-5] for _ in retain_columns_with_na.columns]

        for symbol in symbols:
            expected_dates = self.df_historical_data.filter(like='{}_Date'.format(symbol)).dropna().index.values
            actual_dates = self.market.get_dates(symbols=[symbol])
            self.assertEqual(' '.join(str(expected_dates)), ' '.join(str(actual_dates)))

        expected_dates = self.df_historical_data.loc[dates].filter(regex='(BH|BLFI)_Date').dropna(thresh=1)
        actual_dates = self.market.get_dates(symbols=['BH', 'BLFI'])
        self.assertEqual(len(expected_dates), len(actual_dates))

    def test_get_symbols(self):
        symbols = self.market.get_symbols()
        self.assertEqual(['2GO', 'ABA', 'ABG', 'ABS', 'ABSP', 'AC', 'ACE',
                          'ACR', 'AEV', 'AGI', 'ALCO', 'ALHI', 'ALI',
                          'ANI', 'ANS', 'AP', 'APC', 'APL', 'APO', 'APX',
                          'AR', 'ARA', 'AT', 'ATI', 'ATN', 'ATNB', 'AUB',
                          'BCOR', 'BDO', 'BEL', 'BH', 'BHI', 'BKR', 'BLFI',
                          'BLOOM', 'BPI'], symbols)

    def test_get_quotes_date_symbol(self):
        expected = self.df_historical_data.loc[self.date:self.date].filter(regex='^({})_'.format(self.symbol))
        expected = trim_symbol_from_columns(self.symbol, expected)
        actual = self.market.get_quotes(self.date, self.symbol)
        assert_frame_equal(expected, actual)

    def test_get_quotes_date(self):
        expected = self.df_historical_data.loc[self.date:self.date]
        actual = self.market.get_quotes(self.date)
        assert_frame_equal(expected, actual)

    def test_get_quotes_symbol(self):
        expected = self.df_historical_data.filter(regex='^({})_'.format(self.symbol))
        expected = trim_symbol_from_columns(self.symbol, expected)
        actual = self.market.get_quotes(symbol=self.symbol)
        assert_frame_equal(expected, actual)

    def test_get_quotes(self):
        expected = self.df_historical_data
        actual = self.market.get_quotes()
        assert_frame_equal(expected, actual)

    def test_get_open_date_symbol(self):
        actual = self.market.get_open(self.date, self.symbol)
        self.assertEqual(16.74, actual)

    def test_get_open_date(self):
        expected = self.df_historical_data.loc[self.date:self.date].filter(like='_Open')
        actual = self.market.get_open(self.date)
        assert_frame_equal(expected, actual)

    def test_get_open_symbol(self):
        expected = self.df_historical_data.filter(regex='^{}_Open'.format(self.symbol))
        expected = trim_symbol_from_columns(self.symbol, expected)
        actual = self.market.get_open(symbol=self.symbol)
        assert_frame_equal(expected, actual)

    def test_get_open(self):
        expected = self.df_historical_data.filter(like='Open')
        actual = self.market.get_open()
        assert_frame_equal(expected, actual)


if __name__ == '__main__':
    unittest.main()
