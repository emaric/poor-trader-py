import abc
from enum import Enum, auto


class Direction(Enum):
    LONG = auto()
    SHORT = auto()


class Attribute(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_value(self, date=None, symbol=None, start=None, end=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_indices(self):
        raise NotImplementedError


class Indicator(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, name, attributes):
        self.name = name
        self.attributes = attributes

    @abc.abstractmethod
    def get_attribute(self, key):
        raise NotImplementedError

    @abc.abstractmethod
    def get_attribute_keys(self):
        raise NotImplementedError

    def get_attributes(self):
        return self.attributes

    def get_attribute_value(self, date=None, symbol=None, start=None, end=None, key=None):
        if key is None:
            values = dict()
            for key in self.get_attribute_keys():
                values[key] = self.get_attribute_value(date=date, symbol=symbol, start=start, end=end, key=key)
            return values
        return self.get_attribute(key).get_value(date, symbol, start=start, end=end)

    @abc.abstractmethod
    def get_indices(self):
        raise NotImplementedError

    def is_long(self, date=None, symbol=None):
        return Direction.LONG == self.get_attribute_value(date, symbol, key=Direction.__class__.__name__)

    def is_short(self, date=None, symbol=None):
        return Direction.SHORT == self.get_attribute_value(date, symbol, key=Direction.__class__.__name__)


class Strategy(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, name, indicators=list()):
        self.name = name
        self.indicators = indicators

    def get_long_indicator_names(self, date=None, symbol=None):
        return [i.name for i in self.indicators if i.is_long(date, symbol)]

    def get_short_indicator_names(self, date=None, symbol=None):
        return [i.name for i in self.indicators if i.is_short(date, symbol)]

    def is_long(self, date=None, symbol=None):
        if len(self.indicators) > 0:
            for indicator in self.indicators:
                if not indicator.is_long(date, symbol):
                    return False
            return True
        else:
            return False

    def is_short(self, date=None, symbol=None):
        if len(self.indicators) > 0:
            for indicator in self.indicators:
                if not indicator.is_short(date, symbol):
                    return False
            return True
        else:
            return False


class Screener(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def scan(self, market, start=None, end=None):
        raise NotImplementedError
