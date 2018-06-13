import abc

from poor_trader.market import Market
from poor_trader.screening import entity, indicator
from poor_trader.screening.entity import Direction


class Strategy(entity.Strategy):
    __metaclass__ = abc.ABCMeta

    def __init__(self, indicator_factory: indicator.IndicatorFactory):
        super().__init__(self.__class__.__name__)
        self.indicator_factory = indicator_factory

    @abc.abstractmethod
    def __init_indicators__(self):
        raise NotImplementedError


class ATRChannelBreakout(Strategy):
    def __init__(self, indicator_factory: indicator.IndicatorFactory, top=7, bottom=3, sma=150, fast=100, slow=120):
        super().__init__(indicator_factory)
        self.top = top
        self.bottom = bottom
        self.sma = sma
        self.fast = fast
        self.slow = slow
        self.indicators = self.__init_indicators__() if len(self.indicators) <= 0 else self.indicators

    def __init_indicators__(self):
        atr_channel = self.indicator_factory.create(indicator.ATRChannel, top=self.top, bottom=self.bottom, sma=self.sma)
        ma_cross = self.indicator_factory.create(indicator.MACross, fast=self.fast, slow=self.slow)
        return [atr_channel, ma_cross]


class DonchianChannel(Strategy):
    def __init__(self, indicator_factory: indicator.IndicatorFactory, high=50, low=50, fast=100, slow=120):
        super().__init__(indicator_factory)
        self.high = high
        self.low = low
        self.fast = fast
        self.slow = slow
        self.indicators = self.__init_indicators__() if len(self.indicators) <= 0 else self.indicators

    def __init_indicators__(self):
        donchian_channel = self.indicator_factory.create(indicator.DonchianChannel, high=self.high, low=self.low)
        ma_cross = self.indicator_factory.create(indicator.MACross, fast=self.fast, slow=self.slow)
        return [donchian_channel, ma_cross]

    def entry_condition(self, date, symbol, market: Market, direction=Direction.LONG):
        if direction == Direction.LONG:
            return self.is_long(date, symbol)
        if direction == Direction.SHORT:
            return self.is_short(date, symbol)

    def reentry_condition(self, date, symbol, market: Market, direction=Direction.LONG):
        raise NotImplementedError

    def exit_condition(self, date, symbol, market: Market, entry_date, direction=Direction.LONG):
        exit_direction = Direction.SHORT if direction == Direction.LONG else Direction.LONG
        exit_tags = self.get_indicator_names(direction=exit_direction, date=date, symbol=symbol, start=entry_date)
        entry_tags = self.get_indicator_names(direction=direction, date=date, symbol=symbol, start=entry_date)
        return len([_ for _ in entry_tags if _ not in exit_tags]) <= 0

