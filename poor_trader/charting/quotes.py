from enum import Enum

import numpy as np
import pandas as pd
import matplotlib.dates as mdates
from matplotlib import pylab as plt
from matplotlib.finance import candlestick_ohlc

from poor_trader import config
from poor_trader.charting.entity import ChartItem, OHLC, ChartObject, Subplot
from poor_trader.market import pkl_to_market
from poor_trader.screening.indicator import PickleIndicatorRunnerFactory, DonchianChannel, MACross, \
    PickleIndicatorFactory, Indicator

plt.style.use('ggplot')


class QuoteChartItem(ChartItem):
    class Key(Enum):
        ITEM_INDEX = 'ItemIndex'
        FLOAT_INDEX = 'FloatIndex'

    def __init__(self, indices: list, chart_object_enum: Enum, chart_objects: list, df=None):
        super().__init__(indices, chart_object_enum, chart_objects)
        self.float_index_values_matrix = self.__to_index_values_matrix__(chart_object_enum, chart_objects)
        self.df = df
        self.df = self.__to_dataframe__()

    def get_object_by_position(self, position):
        return self.chart_objects[position]

    def get_object(self, index):
        position = self.df[self.df[self.Key.ITEM_INDEX.value] == index].values[-1]
        return self.get_object_by_position(position)

    def __to_dataframe__(self):
        df = self.df
        if df is None:
            df = pd.DataFrame(index=self.indices)
            for e in self.chart_object_enum:
                df[e.value] = [o[e.value] for o in self.chart_objects]
        df = df.reset_index()
        df[self.Key.ITEM_INDEX.value] = self.indices
        df[self.Key.FLOAT_INDEX.value] = self.float_indices()
        return df
        
    def __to_float__(self, value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return mdates.date2num(pd.to_datetime(value))
    
    def float_indices(self):
        return [self.__to_float__(index) for index in self.indices]

    def get_object_by_floatindex(self, float_index):
        return self.df[self.df[self.Key.FLOAT_INDEX.value] == float_index]

    def get_object_values(self, index=None, chart_object_key=None):
        df = self.df.copy()
        if index is not None:
            df = self.get_object(index)
        if chart_object_key is not None:
            df = df[chart_object_key.value].values
        return df

    def get_object_values_by_floatindex(self, float_index=None, chart_object_key=None):
        df = self.df.copy()
        if float_index is not None:
            df = self.get_object(float_index)
        if chart_object_key is not None:
            df = df[chart_object_key.value].values
        return df

    def __to_value_list__(self, chart_object_enum: Enum, chart_object: ChartObject):
        return [chart_object[e.value] for e in chart_object_enum]

    def __to_index_values_matrix__(self, chart_object_enum: Enum, chart_objects: list):
        return [tuple([i] + self.__to_value_list__(chart_object_enum, chart_objects[i])) for i in self.positions]


class CandlestickSubplot(Subplot):
    def __init__(self, chart_item: QuoteChartItem, width=0.5, colorup='g', colordown='r', edgecolor='b', alpha=0.75, location=0):
        super().__init__(chart_item, location)
        self.width = width
        self.colorup = colorup
        self.colordown = colordown
        self.alpha = alpha
        self.edgecolor = edgecolor

    def plot(self, subplot):
        ls, rs = candlestick_ohlc(subplot, self.chart_item.float_index_values_matrix,
                                  width=self.width, colorup=self.colorup, colordown=self.colordown, alpha=self.alpha)
        [r.set_edgecolor(self.edgecolor) for r in rs]


class FilledSubplot(Subplot):
    def __init__(self, chart_item: QuoteChartItem,
                 top_key, mid_key, bottom_key,
                 top_color, mid_color, bottom_color, location=0):
        super().__init__(chart_item, location)
        self.top_key = top_key
        self.mid_key = mid_key
        self.bottom_key = bottom_key
        self.top_color = top_color
        self.mid_color = mid_color
        self.bottom_color = bottom_color

    def plot(self, subplot):
        subplot.plot(self.chart_item.get_object_values(chart_object_key=self.top_key), color=self.top_color)
        subplot.plot(self.chart_item.get_object_values(chart_object_key=self.mid_key), color=self.mid_color)
        subplot.plot(self.chart_item.get_object_values(chart_object_key=self.bottom_key), color=self.bottom_color)
        subplot.fill_between(range(len(self.chart_item.indices)),
                             self.chart_item.get_object_values(chart_object_key=self.top_key),
                             self.chart_item.get_object_values(chart_object_key=self.bottom_key),
                             color=self.top_color, alpha=0.1)


class LineSubplot(Subplot):
    class Config(object):
        def __init__(self, key, color, linewidth=2):
            self.key = key
            self.color = color
            self.linewidth = linewidth

    def __init__(self, chart_item: QuoteChartItem, *configs: Config, location=0):
        super().__init__(chart_item, location)
        self.configs = configs

    def plot(self, subplot):
        for key_color in self.configs:
            subplot.plot(self.chart_item.get_object_values(chart_object_key=key_color.key),
                         color=key_color.color, linewidth=key_color.linewidth)


def create(quotes: CandlestickSubplot, *subplots: Subplot, title=''):
    ncharts = 1
    plotters = [quotes]
    for _ in subplots:
        plotters.append(_)
        ncharts = max(ncharts, _.location)
    fig = plt.figure(figsize=(20, 5 * ncharts))

    ax1 = None
    for location in range(ncharts):
        ax = plt.subplot(ncharts, 1, location + 1, sharex=ax1)
        if ax1 is None:
            ax1 = ax
        [p.plot(ax) for p in plotters if p.location == location]
        xaxis = quotes.chart_item.positions
        space = 150
        xsize = len(xaxis)
        xticks = np.linspace(0, xsize - 1, space if xsize >= space else xsize, dtype=int)
        ax.set_xticks(xticks)
        xlabels = [pd.to_datetime(quotes.chart_item.indices[i]).strftime(config.DATE_FORMAT) for i in ax.get_xticks()]
        ax.set_xticklabels(xlabels, fontsize=6.5)
        plt.xticks(rotation=90)

    ax1.set_title(title)

    plt.tight_layout()

    plt.show()
    plt.clf()
    plt.close(fig)


def df_to_quote_chart_item(df: pd.DataFrame, keys_enum_class):
    chart_objects = [df.loc[i] for i in df.index.values]
    return QuoteChartItem(df.index.values, keys_enum_class, chart_objects, df=df)


def indicator_to_quote_chart_item(indicator_instance: Indicator, keys_enum_class, symbol, istart, iend):
    indices = indicator_instance.get_indices(keys_enum_class.FAST.value, symbol)[istart:iend]
    chart_objects = [indicator_instance.get_attribute_value(date=date, symbol=symbol) for date in indices]
    return QuoteChartItem(indices, keys_enum_class, chart_objects)


if __name__ == '__main__':
    INDICATORS_PATH = config.TEMP_PATH / 'indicators'
    HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'

    size = 400
    symbol = 'SM'
    market = pkl_to_market('PSE', HISTORICAL_DATA_PATH)
    runner_factory = PickleIndicatorRunnerFactory(INDICATORS_PATH)
    factory = PickleIndicatorFactory(INDICATORS_PATH, market)

    df_quotes = market.get_quotes(symbol=symbol)
    df_donchian = runner_factory.create(DonchianChannel).run(symbol=symbol, df_quotes=df_quotes)
    macross = factory.create(MACross)

    df_quotes = df_quotes.iloc[-size:]
    df_donchian = df_donchian.iloc[-size:]

    quote_chart_item = QuoteChartItem(df_quotes.index.values, OHLC,
                                      [df_quotes.loc[i] for i in df_quotes.index.values], df=df_quotes)
    quote_subplot = CandlestickSubplot(quote_chart_item)

    donchian_chart_item = QuoteChartItem(df_donchian.index.values, DonchianChannel.Columns,
                                         [df_donchian.loc[i] for i in df_donchian.index.values], df=df_donchian)
    donchian_subplot = FilledSubplot(donchian_chart_item,
                                     *[_ for _ in DonchianChannel.Columns],
                                     *['#9160d1', '#b38be8', '#9160d1'])

    macross_chart_item = indicator_to_quote_chart_item(macross, MACross.Columns, symbol, -size, -1)
    macross_subplot = LineSubplot(macross_chart_item,
                                  LineSubplot.Config(MACross.Columns.FAST, '#3af8ff', 2),
                                  LineSubplot.Config(MACross.Columns.SLOW, '#bd3aff', 2))

    create(quote_subplot, donchian_subplot, macross_subplot, title=symbol)


