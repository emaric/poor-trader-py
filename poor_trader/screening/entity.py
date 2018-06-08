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
        if key:
            return self.get_attribute(key).get_value(date, symbol, start=start, end=end)
        else:
            values = dict()
            for key in self.get_attribute_keys():
                values[key] = self.get_attribute_value(date=date, symbol=symbol, start=start, end=end, key=key)
            return values

    @abc.abstractmethod
    def get_indices(self):
        raise NotImplementedError

    def is_long(self, date=None, symbol=None):
        return Direction.LONG == self.get_attribute_value(date, symbol, key=Direction.__name__)

    def is_short(self, date=None, symbol=None):
        return Direction.SHORT == self.get_attribute_value(date, symbol, key=Direction.__name__)


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
        if not self.indicators:
            return False
        elif type(self.indicators) == list:
            return [_ for _ in self.indicators if _.is_long(date, symbol)]
        else:
            raise NotImplementedError

    def is_short(self, date=None, symbol=None):
        if not self.indicators:
            return False
        elif type(self.indicators) == list:
            return [_ for _ in self.indicators if _.is_short(date, symbol)]
        else:
            raise NotImplementedError

    @abc.abstractmethod
    def entry_condition(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def reentry_condition(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def exit_condition(self, *args, **kwargs):
        raise NotImplementedError


class Screener(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def scan(self, market, start=None, end=None):
        raise NotImplementedError
