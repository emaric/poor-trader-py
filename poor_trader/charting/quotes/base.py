from enum import Enum

import numpy as np
import pandas as pd
from matplotlib import pylab as plt
from matplotlib.finance import candlestick_ohlc

from poor_trader import config, utils
from poor_trader.charting.entity import ChartItem, ChartObject, Subplot
from poor_trader.market import pkl_to_market
from poor_trader.screening.indicator import DefaultIndicatorRunnerFactory, DefaultIndicatorFactory
from poor_trader.screening.indicator import DonchianChannel, MACross, TrailingStops, Volume, Indicator

plt.style.use('ggplot')


class OHLC(Enum):
    OPEN = 'Open'
    HIGH = 'High'
    LOW = 'Low'
    CLOSE = 'Close'


class DefaultChartItem(ChartItem):
    INDEX = 'Index'

    def __init__(self, indices: list, chart_object_enum: Enum, chart_objects: list, df=None):
        super().__init__(indices, chart_object_enum, chart_objects)
        self.position_values_matrix = self.__to_position_values_matrix__(chart_object_enum, chart_objects)
        self.df = df
        self.df = self.__to_dataframe__()

    def get_object_by_position(self, position):
        return self.chart_objects[position]

    def get_object(self, index):
        return self.get_object_by_position(self.get_position(index))

    def get_position(self, index):
        return self.df[self.df[self.INDEX] == index].index.values[-1]

    def get_index(self, position):
        return self.indices[position]

    def __to_dataframe__(self):
        df = self.df
        if df is None:
            df = pd.DataFrame(index=self.indices)
            for e in self.chart_object_enum:
                df[e.value] = [o[e.value] for o in self.chart_objects]
        df[self.INDEX] = df.index.values
        df = df.reset_index()
        return df

    def get_object_values(self, index=None, chart_object_key=None):
        df = self.df.copy()
        if index is not None:
            df = self.get_object(index)
        if chart_object_key is not None:
            df = df[chart_object_key.value].values
        return df

    def __to_value_list__(self, chart_object_enum: Enum, chart_object: ChartObject):
        return [chart_object[e.value] for e in chart_object_enum]

    def __to_position_values_matrix__(self, chart_object_enum: Enum, chart_objects: list):
        return [tuple([i] + self.__to_value_list__(chart_object_enum, chart_objects[i])) for i in self.positions]


class CandlestickSubplot(Subplot):
    def __init__(self, chart_item: DefaultChartItem, width=0.5, colorup='g', colordown='r', edgecolor='black', alpha=0.75, location=0, ylabel=''):
        super().__init__(chart_item, location, ylabel)
        self.width = width
        self.colorup = colorup
        self.colordown = colordown
        self.alpha = alpha
        self.edgecolor = edgecolor

    def plot(self, subplot):
        ls, rs = candlestick_ohlc(subplot, self.chart_item.position_values_matrix,
                                  width=self.width, colorup=self.colorup, colordown=self.colordown, alpha=self.alpha)
        [r.set_edgecolor(self.edgecolor) for r in rs]


class BarSubplot(Subplot):
    def __init__(self, chart_item: DefaultChartItem, key, color='green', alpha=0.75, location=1, ylabel=''):
        super().__init__(chart_item, location, ylabel)
        self.key = key
        self.color = color
        self.alpha = alpha

    def plot(self, subplot):
        subplot.bar(self.chart_item.positions,
                    self.chart_item.get_object_values(chart_object_key=self.key),
                    color=self.color, alpha=self.alpha)


class AreaSubplot(Subplot):
    def __init__(self, chart_item: DefaultChartItem, key, color='#469df4', alpha=0.8, location=1, ylabel=''):
        super().__init__(chart_item, location, ylabel)
        self.key = key
        self.color = color
        self.alpha = alpha

    def plot(self, subplot):
        subplot.fill_between(self.chart_item.positions,
                             self.chart_item.get_object_values(chart_object_key=self.key),
                             color=self.color, alpha=self.alpha)


class FilledSubplot(Subplot):
    def __init__(self, chart_item: DefaultChartItem,
                 top_key, mid_key, bottom_key,
                 top_color, mid_color, bottom_color, location=0, ylabel=''):
        super().__init__(chart_item, location, ylabel)
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

    def __init__(self, chart_item: DefaultChartItem, *configs: Config, location=0, ylabel=''):
        super().__init__(chart_item, location, ylabel)
        self.configs = configs

    def plot(self, subplot):
        for key_color in self.configs:
            subplot.plot(self.chart_item.get_object_values(chart_object_key=key_color.key),
                         color=key_color.color, linewidth=key_color.linewidth)


class AXHLineSubplot(Subplot):
    def __init__(self, start_position=0, linewidth=0.5, color='black', location=1, ylabel=''):
        super().__init__(None, location, ylabel)
        self.start_position = start_position
        self.linewidth = linewidth
        self.color = color

    def plot(self, subplot):
        subplot.axhline(self.start_position, linewidth=self.linewidth, color=self.color)


class MarkerSubplot(Subplot):
    def __init__(self, chart_item: DefaultChartItem, key, color='r', shape='v', marker_size=3, location=0, ylabel=''):
        super().__init__(chart_item, location, ylabel)
        self.key = key
        self.color = color
        self.shape = shape
        self.marker_size = marker_size

    def plot(self, subplot):
        subplot.plot(self.chart_item.positions,
                     self.chart_item.get_object_values(chart_object_key=self.key),
                     '{}{}'.format(self.color, self.shape), markersize=self.marker_size)


def create(quotes: CandlestickSubplot, *subplots: Subplot, title='', save_path=None):
    plotters = [quotes]
    for _ in subplots:
        plotters.append(_)
    locations = set([_.location for _ in plotters])
    ncharts = len(locations)
    fig = plt.figure(figsize=(20, 5 * ncharts))

    ax1 = None
    for location in range(ncharts):
        ax = plt.subplot(ncharts, 1, location + 1, sharex=ax1)
        if ax1 is None:
            ax1 = ax
        [(p.plot(ax), ax.set_ylabel(p.ylabel)) for p in plotters if p.location == location]
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

    if save_path:
        utils.makedirs(save_path.parent)
        print('Saving chart', save_path)
        plt.savefig(save_path)
        plt.clf()
        plt.close(fig)
    else:
        plt.show()


def df_to_quote_chart_item(df: pd.DataFrame, keys_enum_class):
    chart_objects = [df.loc[i] for i in df.index.values]
    return DefaultChartItem(df.index.values, keys_enum_class, chart_objects, df=df)


def indicator_to_quote_chart_item(indicator_instance: Indicator, keys_enum_class, symbol, istart=None, iend=None, start=None, end=None):
    indices = indicator_instance.get_indices(symbol=symbol, start=start, end=end)
    indices = indices[istart:] if istart is not None else indices
    indices = indices[:iend] if iend is not None else indices
    chart_objects = [indicator_instance.get_attribute_value(date=date, symbol=symbol) for date in indices]
    return DefaultChartItem(indices, keys_enum_class, chart_objects)


if __name__ == '__main__':
    INDICATORS_PATH = config.TEMP_PATH / 'indicators'
    HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'

    size = 300
    symbol = 'SM'
    market = pkl_to_market('PSE', HISTORICAL_DATA_PATH, symbols=[symbol])
    runner_factory = DefaultIndicatorRunnerFactory(INDICATORS_PATH)
    factory = DefaultIndicatorFactory(INDICATORS_PATH, market)

    df_quotes = market.get_quotes(symbol=symbol)
    df_donchian = runner_factory.create(DonchianChannel).run(symbol=symbol, df_quotes=df_quotes)
    macross = factory.create(MACross)
    trailing_stops = factory.create(TrailingStops)
    volume = factory.create(Volume)

    df_quotes = df_quotes.iloc[-size:]
    df_donchian = df_donchian.iloc[-size:]

    quote_chart_item = df_to_quote_chart_item(df_quotes, OHLC)
    quote_subplot = CandlestickSubplot(quote_chart_item)

    donchian_chart_item = df_to_quote_chart_item(df_donchian, DonchianChannel.Columns)
    donchian_subplot = FilledSubplot(donchian_chart_item,
                                     *[_ for _ in DonchianChannel.Columns],
                                     *['#9160d1', '#b38be8', '#9160d1'])

    macross_chart_item = indicator_to_quote_chart_item(macross, MACross.Columns, symbol, -size, -1)
    macross_subplot = LineSubplot(macross_chart_item,
                                  LineSubplot.Config(MACross.Columns.FAST, '#3af8ff', 2),
                                  LineSubplot.Config(MACross.Columns.SLOW, '#bd3aff', 2))

    trailing_stops_chart_item = indicator_to_quote_chart_item(trailing_stops, TrailingStops.Columns, symbol, -size, -1)
    trailing_stop_subplots = [MarkerSubplot(trailing_stops_chart_item, key=TrailingStops.Columns.LONG, color='r', shape='v'),
                              MarkerSubplot(trailing_stops_chart_item, key=TrailingStops.Columns.SHORT, color='g', shape='^')]

    volume_chart_item = indicator_to_quote_chart_item(volume, Volume.Columns, symbol, -size, -1)
    volume_subplots = [BarSubplot(volume_chart_item, key=Volume.Columns.UP, color='g', alpha=0.75, location=1, ylabel='Volume'),
                       BarSubplot(volume_chart_item, key=Volume.Columns.DOWN, color='r', alpha=0.75, location=1, ylabel='Volume'),
                       AreaSubplot(volume_chart_item, key=Volume.Columns.EMA, location=1, ylabel='Volume')]

    create(quote_subplot, donchian_subplot, macross_subplot,
           *trailing_stop_subplots, *volume_subplots, title=symbol)

