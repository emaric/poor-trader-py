import abc
from enum import Enum, auto


class Direction(Enum):
    LONG = auto()
    SHORT = auto()


class Attribute(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_value(self, date=None, symbol=None):
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

    def get_attribute_value(self, date=None, symbol=None, key='Direction'):
        return self.get_attribute(key).get_value(date, symbol)

    def is_long(self, date=None, symbol=None):
        value = self.get_attribute_value(date, symbol)
        return value == Direction.LONG

    def is_short(self, date=None, symbol=None):
        value = self.get_attribute_value(date, symbol)
        return value == Direction.SHORT


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
