import abc

from poor_trader.screening import entity, indicator


class Strategy(entity.Strategy):
    __metaclass__ = abc.ABCMeta

    def __init__(self, indicator_factory: indicator.IndicatorFactory):
        super().__init__(self.__class__.__name__, self.__init_indicators__(indicator_factory))

    @abc.abstractmethod
    def __init_indicators__(self, factory: indicator.IndicatorFactory):
        raise NotImplementedError


class ATRChannelBreakout(Strategy):
    def __init__(self, indicator_factory: indicator.IndicatorFactory, top=7, bottom=3, sma=150, fast=100, slow=120):
        super().__init__(indicator_factory)
        self.top = top
        self.bottom = bottom
        self.sma = sma
        self.fast = fast
        self.slow = slow

    def __init_indicators__(self, factory: indicator.IndicatorFactory):
        atr_channel = factory.create(indicator.ATRChannel)
        ma_cross = factory.create(indicator.MACross)
        return [atr_channel, ma_cross]
