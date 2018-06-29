import abc

from enum import Enum


class ChartObject(dict):
    def __init__(self, enum_class, *args):
        super().__init__()
        for enum, value in zip(enum_class, args):
            self[enum.value] = value
            self.__dict__[enum.value] = value


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

    @abc.abstractmethod
    def get_position(self, index):
        raise NotImplementedError

    @abc.abstractmethod
    def get_index(self, position):
        raise NotImplementedError


class Subplot(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, chart_item: ChartItem, location, ylabel=''):
        self.chart_item = chart_item
        self.location = location
        self.ylabel = ylabel

    @abc.abstractmethod
    def plot(self, subplot):
        raise NotImplementedError

