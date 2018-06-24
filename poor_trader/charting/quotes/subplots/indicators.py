from poor_trader.charting.quotes.base import DefaultChartItem, LineSubplot, FilledSubplot
from poor_trader.screening.entity import Indicator


def create(indicator: Indicator, keys_enum_class, symbol, start=None, end=None) -> list:
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
    else:
        raise NotImplementedError

