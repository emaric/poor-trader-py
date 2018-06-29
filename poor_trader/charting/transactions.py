from enum import Enum

import pandas as pd

from poor_trader import config, utils
from poor_trader.backtesting.backtester import TransactionKey
from poor_trader.backtesting.entity import Action
from poor_trader.charting.entity import ChartObject, Subplot
from poor_trader.charting.quotes.base import df_to_quote_chart_item, CandlestickSubplot, FilledSubplot, \
    indicator_to_quote_chart_item, LineSubplot, create, DefaultChartItem, OHLC
from poor_trader.market import pkl_to_market
from poor_trader.screening.indicator import DefaultIndicatorRunnerFactory, DefaultIndicatorFactory, DonchianChannel, \
    MACross, ATRChannel, IndicatorFactory, IndicatorRunnerFactory
from poor_trader.charting.quotes.subplots import indicators as plot_i


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

    def __init__(self, quotes_chart_item: DefaultChartItem, open_close_objects: OpenCloseLineObject, config=Config(), location=0):
        super().__init__(quotes_chart_item, location)
        self.quotes_chart_item = quotes_chart_item
        self.open_close_objects = open_close_objects
        self.config = config

    def plot(self, subplot):
        last_position = self.quotes_chart_item.positions[-1]
        last_price = self.quotes_chart_item.get_object_by_position(last_position)[OHLC.CLOSE.value]
        for oc in self.open_close_objects:
            open_position = self.quotes_chart_item.get_position(oc[OpenCloseLineKey.OPEN_INDEX.value])
            close_index = oc[OpenCloseLineKey.CLOSE_INDEX.value]
            close_position = last_position if close_index is None else self.quotes_chart_item.get_position(close_index)

            open_price = oc[OpenCloseLineKey.OPEN_PRICE.value]
            close_price = oc[OpenCloseLineKey.CLOSE_PRICE.value]
            close_price = last_price if close_price is None else close_price

            high = max(self.quotes_chart_item.get_object_values(chart_object_key=OHLC.HIGH))
            low = min(self.quotes_chart_item.get_object_values(chart_object_key=OHLC.LOW))
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


def read_transactions_csv(path):
    df = pd.read_csv(path, index_col=0)
    df[TransactionKey.DATE.value] = pd.to_datetime(df[TransactionKey.DATE.value])
    df[TransactionKey.ACTION.value] = utils.to_enum(df[TransactionKey.ACTION.value], Action)
    return [df.loc[i] for i in df.index.values]


def create_indicator_subplots(transactions, indicator_factory: IndicatorFactory, indicator_runner_factory: IndicatorRunnerFactory, start=None, end=None):
    subplots = []
    indicators_unique_names = set()
    symbol = transactions[0][TransactionKey.SYMBOL.value]
    for t in transactions:
        tags = t[TransactionKey.TAGS.value]
        for indicator_name in tags.split(' '):
            indicators_unique_names.add(indicator_name)
    for unique_name in indicators_unique_names:
        indicator = indicator_factory.create_by_unique_name(unique_name)
        indicator_runner = indicator_runner_factory.create_by_unique_name(unique_name)
        _subplots = plot_i.create(indicator, indicator_runner.Columns, symbol, start=start, end=end)
        subplots = subplots + _subplots
    return subplots


def csv_to_chart(market, transactions_csv_path, save_dir_path=None,
                 indicator_factory: IndicatorFactory=None,
                 indicator_runner_factory: IndicatorRunnerFactory=None):
    transactions = read_transactions_csv(transactions_csv_path)
    symbol_oc_line_items_dict = transactions_to_grouped_open_close_line_items(transactions)
    for symbol in symbol_oc_line_items_dict.keys():
        oc_line_items = symbol_oc_line_items_dict[symbol]
        start = min([_[OpenCloseLineKey.OPEN_INDEX.value] for _ in oc_line_items])
        try:
            end = max([_[OpenCloseLineKey.CLOSE_INDEX.value] for _ in oc_line_items])
        except:
            end = market.get_dates()[-1]
        df_quotes = market.get_quotes(symbol=symbol, start=start, end=end)
        quote_chart_item = df_to_quote_chart_item(df_quotes, OHLC)
        quote_subplot = CandlestickSubplot(quote_chart_item)
        indicator_subplots = create_indicator_subplots([_ for _ in transactions if _[TransactionKey.SYMBOL.value] == symbol],
                                                       indicator_factory,
                                                       indicator_runner_factory,
                                                       start=start, end=end)
        oc_subplot = OpenCloseSubplot(quote_chart_item, oc_line_items)
        save_path = None if save_dir_path is None else save_dir_path / '{}.pdf'.format(symbol)
        print('Creating chart for', symbol)
        create(quote_subplot, *indicator_subplots, oc_subplot, title=symbol, save_path=save_path)


if __name__ == '__main__':
    from poor_trader.charting.quotes.subplots import indicators as subplots_indicators

    INDICATORS_PATH = config.TEMP_PATH / 'indicators'
    HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'
    TRANSACTIONS_DATA_PATH = ((config.RESOURCES_PATH / 'investa') / 'ColFinancialPortfolio') / 'transactions.csv'

    CHARTS_DIR_PATH = TRANSACTIONS_DATA_PATH.parent / 'charts'

    market = pkl_to_market('PSE', HISTORICAL_DATA_PATH)
    runner_factory = DefaultIndicatorRunnerFactory(INDICATORS_PATH)
    factory = DefaultIndicatorFactory(INDICATORS_PATH, market)

    transactions = read_transactions_csv(TRANSACTIONS_DATA_PATH)
    symbol_oc_line_items = transactions_to_grouped_open_close_line_items(transactions)

    donchian = factory.create(DonchianChannel)
    macross = factory.create(MACross, fast=100, slow=120)
    atr_channel = factory.create(ATRChannel)

    symbols = symbol_oc_line_items.keys()
    for symbol in symbols:
        start = pd.to_datetime('2013-08-20')
        end = pd.to_datetime('2013-11-23')
        df_quotes = market.get_quotes(symbol=symbol, start=start, end=end)

        quote_chart_item = df_to_quote_chart_item(df_quotes, OHLC)
        quote_subplot = CandlestickSubplot(quote_chart_item)

        donchian_chart_item = indicator_to_quote_chart_item(donchian, DonchianChannel.Columns, symbol, start=start, end=end)
        donchian_subplot = FilledSubplot(donchian_chart_item,
                                         *[_ for _ in DonchianChannel.Columns],
                                         *['#0033ff', '#6699ff', '#0033ff'])

        atr_channel_chart_item = indicator_to_quote_chart_item(atr_channel, ATRChannel.Columns, symbol, start=start, end=end)
        atr_channel_subplot = FilledSubplot(atr_channel_chart_item,
                                         *[_ for _ in ATRChannel.Columns],
                                         *['#9160d1', '#b38be8', '#9160d1'])

        macross_chart_item = indicator_to_quote_chart_item(macross, MACross.Columns, symbol, start=start, end=end)
        macross_subplot = LineSubplot(macross_chart_item,
                                      LineSubplot.Config(MACross.Columns.FAST, '#3af8ff', 2),
                                      LineSubplot.Config(MACross.Columns.SLOW, '#bd3aff', 2))

        oc_subplot = OpenCloseSubplot(quote_chart_item, symbol_oc_line_items[symbol], location=0)

        create(quote_subplot,
               *subplots_indicators.create(donchian, DonchianChannel.Columns, symbol, start, end),
               *subplots_indicators.create(atr_channel, ATRChannel.Columns, symbol, start, end),
               *subplots_indicators.create(macross, MACross.Columns, symbol, start, end),
               oc_subplot,
               title=symbol)

