from enum import Enum

import pandas as pd

from poor_trader import config
from poor_trader.backtesting.backtester import TransactionKey
from poor_trader.backtesting.entity import Action
from poor_trader.charting.entity import ChartObject, Subplot
from poor_trader.charting.quotes import df_to_quote_chart_item, CandlestickSubplot, FilledSubplot, \
    indicator_to_quote_chart_item, LineSubplot, create, QuoteChartItem
from poor_trader.market import pkl_to_market
from poor_trader.screening import strategy
from poor_trader.screening.indicator import PickleIndicatorRunnerFactory, PickleIndicatorFactory, DonchianChannel, \
    MACross


class OpenCloseLineKey(Enum):
    OPEN_INDEX = 'OpenIndex'
    CLOSE_INDEX = 'CloseIndex'
    OPEN_PRICE = 'OpenPrice'
    CLOSE_PRICE = 'ClosePrice'


class OpenCloseLineObject(ChartObject):
    def __init__(self, open_index, close_index, open_price, close_price):
        super().__init__(OpenCloseLineKey, open_index, close_index, open_price, close_price)


class OpenCloseSubplot(Subplot):
    class Config(object):
        def __init__(self, loss_color='#ff00fa', win_color='#21ff24', open_marker='^', close_marker='v',
                     linewidth=2, marker_size=6, marker_edge_width=0.5, marker_edge_color='black', point_shape='o',
                     line_style='-', open_line_style='--'):
            self.loss_color = loss_color
            self.win_color = win_color
            self.open_marker = open_marker
            self.close_marker = close_marker
            self.line_width = linewidth
            self.marker_size = marker_size
            self.marker_edge_color = marker_edge_color
            self.point_shape = point_shape
            self.marker_edge_width = marker_edge_width
            self.line_style = line_style
            self.open_line_style = open_line_style

    def __init__(self, quotes_chart_item: QuoteChartItem, open_close_objects: OpenCloseLineObject, config=Config(), location=0):
        super().__init__(quotes_chart_item, location)
        self.quotes_chart_item = quote_chart_item
        self.open_close_objects = open_close_objects
        self.config = config

    def plot(self, subplot):
        last_position = quote_chart_item.positions[-1]
        last_price = quote_chart_item.get_object_by_position(last_position)[OHLC.CLOSE.value]
        for oc in self.open_close_objects:
            open_position = quote_chart_item.get_position(oc[OpenCloseLineKey.OPEN_INDEX.value])
            close_index = oc[OpenCloseLineKey.CLOSE_INDEX.value]
            close_position = last_position if close_index is None else quote_chart_item.get_position(close_index)

            open_price = oc[OpenCloseLineKey.OPEN_PRICE.value]
            close_price = oc[OpenCloseLineKey.CLOSE_PRICE.value]
            close_price = last_price if close_price is None else close_price

            high = max(quote_chart_item.get_object_values(chart_object_key=OHLC.HIGH))
            low = min(quote_chart_item.get_object_values(chart_object_key=OHLC.LOW))
            marker_space = (high - low) / 30

            subplot.plot((open_position, close_position), (open_price, close_price),
                         '{}{}'.format(self.config.point_shape, self.config.line_style if close_index else self.config.open_line_style),
                         linewidth=self.config.line_width, markersize=self.config.marker_size * 0.7,
                         color='{}'.format(self.config.loss_color if open_price >= close_price else self.config.win_color))
            subplot.plot(open_position, (open_price - marker_space),
                         color=self.config.win_color, marker=self.config.open_marker,
                         markersize=self.config.marker_size, markeredgecolor=self.config.marker_edge_color,
                         markeredgewidth=self.config.marker_edge_width)
            subplot.plot(close_position, (close_price + marker_space),
                         color=self.config.loss_color, marker=self.config.close_marker,
                         markersize=self.config.marker_size, markeredgecolor=self.config.marker_edge_color,
                         markeredgewidth=self.config.marker_edge_width)


def transactions_to_open_close_line_items(transactions):
    open_close_transactions = []
    for transaction in transactions:
        if open_close_transactions:
            last = open_close_transactions[-1][-1]
            if last[TransactionKey.ACTION.value] == Action.OPEN:
                open_close_transactions[-1].append(transaction)
            if last[TransactionKey.ACTION.value] == Action.CLOSE:
                open_close_transactions.append([transaction])
        else:
            open_close_transactions.append([transaction])

    open_close_line_items = []
    for open_close_transaction in open_close_transactions:
        close_transaction = {TransactionKey.DATE.value: None, TransactionKey.PRICE.value: None}
        last = open_close_transaction[-1]
        if last[TransactionKey.ACTION.value] == Action.CLOSE:
            close_transaction = last
        for open_transaction in open_close_transaction:
            if open_transaction[TransactionKey.ACTION.value] == Action.OPEN:
                oc_line = OpenCloseLineObject(pd.to_datetime(open_transaction[TransactionKey.DATE.value]),
                                              pd.to_datetime(close_transaction[TransactionKey.DATE.value]),
                                              open_transaction[TransactionKey.PRICE.value],
                                              close_transaction[TransactionKey.PRICE.value])
                open_close_line_items.append(oc_line)
    return open_close_line_items


def group_transactions(transactions, key=TransactionKey.SYMBOL):
    grouped = dict()
    for transaction in transactions:
        transaction_key = transaction[key.value]
        if transaction_key in grouped.keys():
            grouped[transaction_key].append(transaction)
        else:
            grouped[transaction_key] = [transaction]
    return grouped


def transactions_to_grouped_open_close_line_items(transactions, key=TransactionKey.SYMBOL):
    return_value = dict()
    grouped = group_transactions(transactions, key)
    for k in grouped.keys():
        return_value[k] = transactions_to_open_close_line_items(grouped[k])
    return return_value


if __name__ == '__main__':
    from poor_trader.charting.quotes import OHLC

    INDICATORS_PATH = config.TEMP_PATH / 'indicators'
    HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'
    TRANSACTIONS_DATA_PATH = (config.RESOURCES_PATH / 'ColFinancialPortfolio') / 'transactions.pkl'

    CHARTS_DIR_PATH = TRANSACTIONS_DATA_PATH.parent / 'charts'

    market = pkl_to_market('PSE', HISTORICAL_DATA_PATH)
    runner_factory = PickleIndicatorRunnerFactory(INDICATORS_PATH)
    factory = PickleIndicatorFactory(INDICATORS_PATH, market)

    df = pd.read_pickle(TRANSACTIONS_DATA_PATH)
    df[TransactionKey.DATE.value] = pd.to_datetime(df[TransactionKey.DATE.value])
    transactions = [df.loc[i] for i in df.index.values]
    symbol_oc_line_items = transactions_to_grouped_open_close_line_items(transactions)

    donchian = factory.create(DonchianChannel)
    macross = factory.create(MACross)

    symbols = symbol_oc_line_items.keys()
    for symbol in symbols:
        df_symbol_transactions = df[df[TransactionKey.SYMBOL.value] == symbol]
        start = df_symbol_transactions[TransactionKey.DATE.value].min()
        end = None
        df_quotes = market.get_quotes(symbol=symbol, start=start, end=end)

        quote_chart_item = df_to_quote_chart_item(df_quotes, OHLC)
        quote_subplot = CandlestickSubplot(quote_chart_item)

        donchian_chart_item = indicator_to_quote_chart_item(donchian, DonchianChannel.Columns, symbol, start=start, end=end)
        donchian_subplot = FilledSubplot(donchian_chart_item,
                                         *[_ for _ in DonchianChannel.Columns],
                                         *['#9160d1', '#b38be8', '#9160d1'])

        macross_chart_item = indicator_to_quote_chart_item(macross, MACross.Columns, symbol, start=start, end=end)
        macross_subplot = LineSubplot(macross_chart_item,
                                      LineSubplot.Config(MACross.Columns.FAST, '#3af8ff', 2),
                                      LineSubplot.Config(MACross.Columns.SLOW, '#bd3aff', 2))

        oc_subplot = OpenCloseSubplot(quote_chart_item, symbol_oc_line_items[symbol])

        create(quote_subplot, donchian_subplot, macross_subplot, oc_subplot,
               title=symbol, save_path=CHARTS_DIR_PATH / '{}.pdf'.format(symbol))

