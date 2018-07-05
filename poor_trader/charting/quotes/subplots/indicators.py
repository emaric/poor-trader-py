from poor_trader.charting.quotes.base import DefaultChartItem, LineSubplot, FilledSubplot, AXHLineSubplot, BarSubplot, \
    AreaSubplot
from poor_trader.screening.entity import Indicator
from poor_trader.screening.indicator import MACross, DonchianChannel, ATRChannel, TrendStrength, Volume, \
    PriceVolumeTrend


def create(indicator: Indicator, keys_enum_class, symbol, start=None, end=None, bottom_plot_location=1) -> list:
    indices = indicator.get_indices(symbol=symbol, start=start, end=end)
    chart_objects = [indicator.get_attribute_value(date=date, symbol=symbol) for date in indices]
    chart_item = DefaultChartItem(indices, keys_enum_class, chart_objects)

    if MACross.is_unique_name_a_match(indicator.name):
        return [LineSubplot(chart_item,
                            LineSubplot.Config(MACross.Columns.FAST, '#3e9def', 2),
                            LineSubplot.Config(MACross.Columns.SLOW, '#2f77b6', 2))]
    elif DonchianChannel.is_unique_name_a_match(indicator.name):
        return [FilledSubplot(chart_item,
                              *[_ for _ in DonchianChannel.Columns],
                              *['#a92bbb', '#ad80bb', '#a92bbb'])]
    elif ATRChannel.is_unique_name_a_match(indicator.name):
        return [FilledSubplot(chart_item,
                              *[_ for _ in ATRChannel.Columns],
                              *['#bb294f', '#bb6471', '#bb294f'])]
    elif TrendStrength.is_unique_name_a_match(indicator.name):
        ylabel = 'Trend Strength {} {} {}'.format(*TrendStrength.get_init_param_values(indicator.name).values())
        return [LineSubplot(chart_item,
                            *[LineSubplot.Config(sma, 'r', 0.5) for sma in keys_enum_class
                              if sma.value != TrendStrength.Columns.TREND_STRENGTH.value]),
                LineSubplot(chart_item,
                            LineSubplot.Config(TrendStrength.Columns.TREND_STRENGTH, 'r', 0.5),
                            location=bottom_plot_location,
                            ylabel=ylabel),
                AXHLineSubplot(location=bottom_plot_location,
                               ylabel=ylabel)]
    elif Volume.is_unique_name_a_match(indicator.name):
        ylabel = 'Volume {}'.format(*Volume.get_init_param_values(indicator.name).values())
        return [BarSubplot(chart_item, key=Volume.Columns.UP, color='g', alpha=0.75, location=bottom_plot_location, ylabel=ylabel),
                BarSubplot(chart_item, key=Volume.Columns.DOWN, color='r', alpha=0.75, location=bottom_plot_location, ylabel=ylabel),
                AreaSubplot(chart_item, key=Volume.Columns.EMA, location=bottom_plot_location, ylabel=ylabel)]
    elif PriceVolumeTrend.is_unique_name_a_match(indicator.name):
        ylabel = 'PVT'
        return [LineSubplot(chart_item,
                            LineSubplot.Config(PriceVolumeTrend.Columns.PVT, 'black', 1),
                            LineSubplot.Config(PriceVolumeTrend.Columns.FAST_MA, 'blue', 0.5),
                            LineSubplot.Config(PriceVolumeTrend.Columns.SLOW_MA, 'red', 0.5),
                            location=bottom_plot_location,
                            ylabel=ylabel)]
    else:
        raise NotImplementedError

