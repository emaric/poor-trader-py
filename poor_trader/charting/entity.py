import abc

from enum import Enum


class ChartObject(object):
    def __init__(self, enum_class, *args):
        for enum, value in zip(enum_class, args):
            self.__dict__[enum.value] = value

    def get_value(self, key: Enum):
        return self.__dict__[key.value]

    def __str__(self):
        return str(self.__dict__)


class EquityCurveKey(Enum):
    EQUITY = 'Equity'
    CASH = 'Cash'
    DRAWDOWN = 'Drawdown'
    DRAWDOWN_PERCENT = 'DrawdownPercent'


class EquityCurveItem(ChartObject):
    def __init__(self, equity=100000.0, cash=100000.0, drawdown=0.0, drawdown_percent=0.0):
        super().__init__(EquityCurveKey, equity, cash, drawdown, drawdown_percent)


class OpenCloseLineKey(Enum):
    OPEN_INDEX = 'OpenIndex'
    CLOSE_INDEX = 'CloseIndex'
    OPEN_PRICE = 'OpenPrice'
    CLOSE_PRICE = 'ClosePrice'


class OpenCloseLineItem(ChartObject):
    def __init__(self, open_index, close_index, open_price, close_price):
        super().__init__(OpenCloseLineKey, open_index, close_index, open_price, close_price)


class EquityCurveChart(object):
    def __init__(self, indices=list(), equity_curve_items=list(), index_labels=list()):
        self.indices = indices
        self.equity_curve_items = equity_curve_items
        self.index_labels = indices if len(index_labels) <= 0 else index_labels


class OHLC(Enum):
    OPEN = 'Open'
    HIGH = 'High'
    LOW = 'Low'
    CLOSE = 'Close'


class ChartItem(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, indices: list, chart_object_enum: Enum, chart_objects: list):
        self.indices = indices
        self.chart_object_enum = chart_object_enum
        self.chart_objects = chart_objects
        self.positions = range(len(indices))

    @abc.abstractmethod
    def get_object(self, index):
        raise NotImplementedError

    @abc.abstractmethod
    def get_object_by_position(self, position):
        raise NotImplementedError


class Subplot(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, chart_item: ChartItem, location):
        self.chart_item = chart_item
        self.location = location

    @abc.abstractmethod
    def plot(self, subplot):
        raise NotImplementedError
