import os
import shutil
import unittest

import pandas as pd
from path import Path
from poor_trader import config, utils
from poor_trader.backtesting import chart
from poor_trader.backtesting.backtester import TransactionKey
from poor_trader.backtesting.chart import OpenCloseLine
from poor_trader.backtesting.entity import Action
from poor_trader.charting.transactions import transactions_to_grouped_open_close_line_items
from poor_trader.market import csv_to_market
from poor_trader.screening.indicator import MACross, ATRChannel
from tests import test_indicator

TRANSACTIONS_PATH = config.TEST_RESOURCES_PATH / 'transactions.csv'
CHART_FILE_PATH_PATTERN = str((config.TEST_TEMP_PATH / 'charts') / '{}.pdf')


class TestChart(unittest.TestCase):
    def setUp(self):
        self.tearDown()
        self.market = csv_to_market('TestMarket', test_indicator.INTRADAY_HISTORICAL_DATA_PATH)

    def tearDown(self):
        if os.path.exists(config.TEST_TEMP_PATH):
            shutil.rmtree(config.TEST_TEMP_PATH)

    def test_transactions(self):
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('CEB')))
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('EW')))
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('JFC')))
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('NOW')))
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('SM')))

        df = pd.read_csv(TRANSACTIONS_PATH)
        df[TransactionKey.ACTION.value] = utils.to_enum(df[TransactionKey.ACTION.value], Action)
        transactions = [df.loc[i] for i in df.index.values]
        symbol_oc_line_items = transactions_to_grouped_open_close_line_items(transactions)

        symbols = set(df[TransactionKey.SYMBOL.value].values)
        for symbol in symbols:
            df_symbol_transactions = df[df[TransactionKey.SYMBOL.value] == symbol]
            df_ma_cross = MACross(fast=5, slow=10).run(symbol, self.market.get_quotes(symbol=symbol))
            df_atr_channel = ATRChannel(top=7, bottom=3, sma=10).run(symbol, self.market.get_quotes(symbol=symbol))

            df_quotes = self.market.get_quotes(symbol=symbol,
                                               start=df_symbol_transactions[TransactionKey.DATE.value].min(),
                                               end=df_symbol_transactions[TransactionKey.DATE.value].max())
            df_ma_cross = df_ma_cross.loc[df_quotes.index]
            df_atr_channel = df_atr_channel.loc[df_quotes.index]
            df_dohlc = chart.to_dohlc(df_quotes)
            chart.ohlc_chart(df_dohlc, title=symbol, open_close_line_list=symbol_oc_line_items[symbol],
                             bollinger_band=df_atr_channel,
                             ma_cross=df_ma_cross,
                             save_path=Path(CHART_FILE_PATH_PATTERN.format(symbol)),
                             size_pct=0.2)

        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('CEB')))
        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('EW')))
        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('JFC')))
        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('NOW')))
        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('SM')))

    def test_chart_transactions_df(self):
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('CEB')))
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('EW')))
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('JFC')))
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('NOW')))
        self.assertFalse(os.path.exists(CHART_FILE_PATH_PATTERN.format('SM')))

        df = pd.read_csv(TRANSACTIONS_PATH)
        df[TransactionKey.ACTION.value] = utils.to_enum(df[TransactionKey.ACTION.value], Action)
        symbols = set(df[TransactionKey.SYMBOL.value].values)
        for symbol in symbols:
            open_close_lines = []
            df_symbol_transactions = df[df[TransactionKey.SYMBOL.value] == symbol]
            df_transactions = df_symbol_transactions.copy()
            df_close = df_transactions[df_transactions[TransactionKey.ACTION.value] == Action.CLOSE]
            close_indices = list(df_close.index.values)
            if df_close.empty or df_symbol_transactions[TransactionKey.ACTION.value].iloc[-1] == Action.OPEN:
                close_indices.append(df_symbol_transactions.iloc[-1:].index.values[0])
            print(close_indices)
            for close_i in pd.Index(close_indices):
                df_opens = df_transactions[df_transactions[TransactionKey.ACTION.value].isin([Action.OPEN])].loc[:close_i]
                df_transactions = df_transactions.loc[close_i:].iloc[1:]
                for open_i in df_opens.index.values:
                    s_open = df_opens.loc[open_i]
                    s_close = df_symbol_transactions.loc[close_i]
                    open_close_lines.append(pd.Series({OpenCloseLine.OPEN_INDEX.value: s_open[TransactionKey.DATE.value],
                                                       OpenCloseLine.CLOSE_INDEX.value: s_close[TransactionKey.DATE.value],
                                                       OpenCloseLine.OPEN_PRICE.value: s_open[TransactionKey.PRICE.value],
                                                       OpenCloseLine.CLOSE_PRICE.value: s_close[TransactionKey.PRICE.value]}))
            print(df_symbol_transactions)
            df_ma_cross = MACross(fast=5, slow=10).run(symbol, self.market.get_quotes(symbol=symbol))
            df_atr_channel = ATRChannel(top=7, bottom=3, sma=10).run(symbol, self.market.get_quotes(symbol=symbol))

            df_quotes = self.market.get_quotes(symbol=symbol,
                                               start=df_symbol_transactions[TransactionKey.DATE.value].min(),
                                               end=df_symbol_transactions[TransactionKey.DATE.value].max())
            df_ma_cross = df_ma_cross.loc[df_quotes.index]
            df_atr_channel = df_atr_channel.loc[df_quotes.index]
            df_dohlc = chart.to_dohlc(df_quotes)
            chart.ohlc_chart(df_dohlc, title=symbol, open_close_line_list=open_close_lines,
                             bollinger_band=df_atr_channel,
                             ma_cross=df_ma_cross,
                             save_path=Path(CHART_FILE_PATH_PATTERN.format(symbol)),
                             size_pct=0.2)

        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('CEB')))
        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('EW')))
        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('JFC')))
        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('NOW')))
        self.assertTrue(os.path.exists(CHART_FILE_PATH_PATTERN.format('SM')))


if __name__ == '__main__':
    unittest.main()
