import abc
import os
import inspect
from enum import Enum

import numpy as np
import pandas as pd
from path import Path

from poor_trader.market import Market, pkl_to_market
from poor_trader.screening import entity
from poor_trader import config, utils
from poor_trader.screening.entity import Direction


class IndicatorRunnerFactory(object):
    __metaclass__ = abc.ABCMeta

    def create(self, cls, *args, **kwargs):
        runner = cls(*args, **kwargs)
        runner.factory = self
        return runner

    def create_by_unique_name(self, unique_name):
        indicator_runner_classes = IndicatorRunner.__subclasses__()
        for indicator_runner_class in indicator_runner_classes:
            if indicator_runner_class.is_unique_name_a_match(unique_name):
                return self.create(indicator_runner_class,
                                   **indicator_runner_class.get_init_param_values(unique_name))


class IndicatorRunner(object):
    __metaclass__ = abc.ABCMeta

    class Columns(Enum):
        pass

    def __init__(self, name, param_values):
        self.name = name
        self.unique_name = self.__init_unique_name__(self.name,
                                                     inspect.signature(self.__init__).parameters,
                                                     param_values)
        self.factory = IndicatorRunnerFactory()

    @abc.abstractmethod
    def run(self, symbol, df_quotes, df_indicator=None):
        raise NotImplementedError

    @staticmethod
    def add_direction(df, long_condition, short_condition):
        df[Direction.__name__] = np.where(long_condition, entity.Direction.LONG,
                                   np.where(short_condition, entity.Direction.SHORT, ''))

    @staticmethod
    def is_updated(df_quotes, df_indicator):
        if df_indicator is None:
            return False
        return pd.Index.equals(df_quotes.index, df_indicator.index)

    @staticmethod
    def __init_unique_name__(name, parameters, param_values):
        return str(Path(name + '_' + '_'.join([str(param_values[parameter]) for parameter in parameters])))

    @classmethod
    def is_unique_name_a_match(cls, unique_name):
        parameters = [_ for _ in inspect.signature(cls.__init__).parameters if _ != 'self']
        sub_strs = unique_name.split('_')
        return sub_strs[0] == cls.__name__ and len(parameters) == len(sub_strs) - 1

    @classmethod
    def get_init_param_values(cls, unique_name):
        return_values = {}
        values = unique_name.split('_')
        parameters = inspect.signature(cls.__init__).parameters
        for i, (name, param) in enumerate(parameters.items()):
            if i == 0: continue
            param_type = type(param.default)
            return_values[name] = param_type(values[i])
        return return_values


class STDEV(IndicatorRunner):
    def __init__(self, period=10, field='Close'):
        super().__init__(self.__class__.__name__, locals())
        self.period = period
        self.field = field

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator
        df = pd.DataFrame(index=df_quotes.index)
        df['STDEV'] = df_quotes[self.field].rolling(self.period).std()
        self.add_direction(df, df_quotes[self.field] > df['STDEV'], df_quotes[self.field] < df['STDEV'])
        df = utils.round_df(df)
        return df


class EMA(IndicatorRunner):
    def __init__(self, period=10, field='Close'):
        super().__init__(self.__class__.__name__, locals())
        self.period = period
        self.field = field

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator
        c = 2./(self.period + 1.)
        df = pd.DataFrame(columns=['EMA'], index=df_quotes.index)
        _sma = self.factory.create(SMA, period=self.period, field=self.field).run(symbol, df_quotes).dropna()
        if not _sma.empty:
            df.loc[_sma.index.values[0], 'EMA'] = _sma.SMA.values[0]
            for i in range(1, len(df_quotes)):
                prev_ema = df.iloc[i-1]
                if pd.isnull(prev_ema.EMA): continue
                price = df_quotes.iloc[i]
                ema_value = c * price[self.field] + (1. - c) * prev_ema.EMA
                df.loc[df_quotes.index.values[i], 'EMA'] = ema_value

        self.add_direction(df, df_quotes[self.field] > df['EMA'], df_quotes[self.field] < df['EMA'])
        df = utils.round_df(df)
        return df


class SMA(IndicatorRunner):
    def __init__(self, period=10, field='Close'):
        super().__init__(self.__class__.__name__, locals())
        self.period = period
        self.field = field

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator
        else:
            df = pd.DataFrame(index=df_quotes.index)
            df['SMA'] = df_quotes[self.field].rolling(self.period).mean()
            self.add_direction(df, df_quotes[self.field] > df['SMA'], df_quotes[self.field] < df['SMA'])
            df = utils.round_df(df)
            return df


class ATR(IndicatorRunner):
    def __init__(self, period=10):
        super().__init__(self.__class__.__name__, locals())
        self.period = period

    def true_range(self, df_quotes):
        df = pd.DataFrame(index=df_quotes.index)
        df['n_index'] = range(len(df_quotes))
        def _true_range(indices):
            _df_quotes = df_quotes.iloc[indices]
            a = utils.roundn(np.abs(_df_quotes.High - _df_quotes.Low)[-1], 4)
            b = utils.roundn(np.abs(_df_quotes.High - _df_quotes.shift(1).Close)[-1], 4)
            c = utils.roundn(np.abs(_df_quotes.Low - _df_quotes.shift(1).Close)[-1], 4)
            return max(a, b, c)
        df['true_range'] = df.n_index.rolling(2).apply(_true_range)
        return df.filter(like='true_range')

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        df = pd.DataFrame(columns=['ATR'], index=df_quotes.index)
        df_true_range = self.true_range(df_quotes)
        for i in range(1+len(df_quotes)-self.period):
            if pd.isnull(df_true_range.iloc[i].true_range): continue
            start = i
            end = i + self.period
            last_index = end - 1
            trs = df_true_range[start:end]
            prev_atr = df.iloc[last_index-1].ATR
            if pd.isnull(prev_atr):
                atr = np.mean([tr for tr in trs.true_range.values])
            else:
                atr = (prev_atr * (self.period-1) + df_true_range.iloc[last_index].true_range) / self.period
            df.loc[df_quotes.index.values[last_index], 'ATR'] = atr
        self.add_direction(df, False, False)
        return utils.round_df(df)


class ATRChannel(IndicatorRunner):
    class Columns(Enum):
        TOP = 'Top'
        MID = 'Mid'
        BOTTOM = 'Bottom'

    def __init__(self, top=7, bottom=3, sma=150):
        super().__init__(self.__class__.__name__, locals())
        self.top = top
        self.bottom = bottom
        self.sma = sma

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        df_top_atr = self.factory.create(ATR, period=self.top).run(symbol, df_quotes)
        df_bottom_atr = self.factory.create(ATR, period=self.bottom).run(symbol, df_quotes)
        df_sma = self.factory.create(SMA, period=self.sma).run(symbol, df_quotes)
        df = pd.DataFrame(columns=[_.value for _ in self.Columns], index=df_quotes.index)
        df[self.Columns.MID.value] = df_sma.SMA
        df[self.Columns.TOP.value] = df[self.Columns.MID.value] + df_top_atr.ATR
        df[self.Columns.BOTTOM.value] = df[self.Columns.MID.value] - df_bottom_atr.ATR
        self.add_direction(df, df_quotes.Close > df[self.Columns.TOP.value], df_quotes.Close < df[self.Columns.BOTTOM.value])
        df = utils.round_df(df)
        return df


class TrailingStops(IndicatorRunner):
    class Columns(Enum):
        LONG = 'BuyStops'
        SHORT = 'SellStops'

    def __init__(self, multiplier=4, period=10):
        super().__init__(self.__class__.__name__, locals())
        self.multiplier = multiplier
        self.period = period

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        df = pd.DataFrame(columns=['BuyStops', 'SellStops'], index=df_quotes.index)
        df_atr = self.factory.create(ATR, period=self.period).run(symbol, df_quotes)
        sign = -1  # SellStops: -1, BuyStops: 1
        for i in range(len(df_quotes)-1):
            if pd.isnull(df_atr.iloc[i].ATR): continue
            start = i - self.period
            end = i
            quotes = df_quotes.iloc[start+1:end+1]
            cur_quote = df_quotes.iloc[i]
            next_quote = df_quotes.iloc[i + 1]
            _atr = df_atr.iloc[i].ATR

            # close_price = next_quote.Close
            # trend_dir_sign = -1 if close_price > _atr else 1

            max_price = quotes.Close.max()
            min_price = quotes.Close.min()

            sell = max_price + sign * (self.multiplier * _atr)
            buy = min_price + sign * (self.multiplier * _atr)

            sell = [sell, df.iloc[i].SellStops]
            buy = [buy, df.iloc[i].BuyStops]

            try:
                sell = np.max([x for x in sell if not pd.isnull(x)])
                buy = np.min([x for x in buy if not pd.isnull(x)])
            except:
                print(sell)

            if sign < 0:
                df.loc[df_quotes.index.values[i+1]]['SellStops'] = sell
                if next_quote.Close <= sell:
                    sign = 1
            else:
                df.loc[df_quotes.index.values[i+1]]['BuyStops'] = buy
                if next_quote.Close >= buy:
                    sign = -1

        self.add_direction(df, df_quotes.Close >= df.BuyStops, df_quotes.Close <= df.SellStops)
        df = utils.round_df(df)
        return df


class DonchianChannel(IndicatorRunner):
    class Columns(Enum):
        HIGH = 'High'
        MID = 'Mid'
        LOW = 'Low'

    def __init__(self, high=50, low=50):
        super().__init__(self.__class__.__name__, locals())
        self.high = high
        self.low = low

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        df = pd.DataFrame(columns=[_.value for _ in self.Columns], index=df_quotes.index)
        df[self.Columns.HIGH.value] = df_quotes.High.rolling(window=self.high).max()
        df[self.Columns.LOW.value] = df_quotes.Low.rolling(window=self.low).min()
        df[self.Columns.MID.value] = (df[self.Columns.HIGH.value] + df[self.Columns.LOW.value])/2

        self.add_direction(df, np.logical_and(df[self.Columns.HIGH.value].shift(1) < df[self.Columns.HIGH.value],
                                              df[self.Columns.LOW.value].shift(1) <= df[self.Columns.LOW.value]),
                           np.logical_and(df[self.Columns.LOW.value].shift(1) > df[self.Columns.LOW.value],
                                          df[self.Columns.HIGH.value].shift(1) >= df[self.Columns.HIGH.value]))
        df = utils.round_df(df)
        return df


class MACD(IndicatorRunner):
    def __init__(self, fast=12, slow=26, signal=9):
        super().__init__(self.__class__.__name__, locals())
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        df = pd.DataFrame(index=df_quotes.index)
        fast_ema = self.factory.create(EMA, period=self.fast).run(symbol, df_quotes)
        slow_ema = self.factory.create(EMA, period=self.slow).run(symbol, df_quotes)
        df['MACD'] = fast_ema.EMA - slow_ema.EMA
        signal_ema = self.factory.create(EMA, period=self.signal, field='MACD').run(symbol, df)
        df['Signal'] = signal_ema.EMA
        df['MACDCrossoverSignal'] = np.where(np.logical_and(df.MACD > df.Signal, df.MACD.shift(1) <= df.Signal.shift(1)), 1, 0)
        df['SignalCrossoverMACD'] = np.where(np.logical_and(df.MACD < df.Signal, df.Signal.shift(1) <= df.MACD.shift(1)), 1, 0)
        self.add_direction(df, df['MACDCrossoverSignal'] == 1, df['SignalCrossoverMACD'] == 1)
        df = utils.round_df(df)
        return df


class MACross(IndicatorRunner):
    class Columns(Enum):
        FAST = 'FastSMA'
        SLOW = 'SlowSMA'
        FAST_ON_TOP = 'FastCrossoverSlow'
        SLOW_ON_TOP = 'SlowCrossoverFast'

    def __init__(self, fast=40, slow=60):
        super().__init__(self.__class__.__name__, locals())
        self.fast = fast
        self.slow = slow

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        df = pd.DataFrame(index=df_quotes.index)
        fast_sma = self.factory.create(SMA, period=self.fast).run(symbol, df_quotes)
        slow_sma = self.factory.create(SMA, period=self.slow).run(symbol, df_quotes)
        df[self.Columns.FAST.value] = fast_sma.SMA
        df[self.Columns.SLOW.value] = slow_sma.SMA
        df[self.Columns.SLOW_ON_TOP.value] = np.where(np.logical_and(df[self.Columns.FAST.value] <= df[self.Columns.SLOW.value], df[self.Columns.FAST.value].shift(1) > df[self.Columns.SLOW.value].shift(1)), 1, 0)
        df[self.Columns.FAST_ON_TOP.value] = np.where(np.logical_and(df[self.Columns.FAST.value] >= df[self.Columns.SLOW.value], df[self.Columns.SLOW.value].shift(1) > df[self.Columns.FAST.value].shift(1)), 1, 0)
        self.add_direction(df, df[self.Columns.FAST.value] > df[self.Columns.SLOW.value], df[self.Columns.SLOW.value] > df[self.Columns.FAST.value])
        df = utils.round_df(df)
        return df


class Volume(IndicatorRunner):
    class Columns(Enum):
        VOLUME = 'Volume'
        EMA = 'EMA'
        UP = 'Up'
        DOWN = 'Down'

    def __init__(self, period=20):
        super().__init__(self.__class__.__name__, locals())
        self.period = period

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        df = pd.DataFrame(index=df_quotes.index)
        ema = self.factory.create(EMA, period=self.period, field='Volume').run(symbol, df_quotes)
        df['Volume'] = df_quotes.Volume
        df['EMA'] = ema.EMA
        df[self.Columns.UP.value] = np.where(df_quotes.Open < df_quotes.Close, df_quotes.Volume, 0)
        df[self.Columns.DOWN.value] = np.where(df_quotes.Open >= df_quotes.Close, df_quotes.Volume, 0)

        self.add_direction(df, np.logical_and(df['Volume'] > df['EMA'], df['Volume'].shift(1) < df['EMA'].shift(1)),
                           np.logical_and(df['Volume'] < df['EMA'], df['Volume'].shift(1) > df['EMA'].shift(1)))
        df = utils.round_df(df)
        return df


class TrendStrength(IndicatorRunner):
    def __init__(self, start=40, end=150, step=5):
        super().__init__(self.__class__.__name__, locals())
        self.start = start
        self.end = end
        self.step = step

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        df = pd.DataFrame(index=df_quotes.index)
        columns = [x for x in range(self.start, self.end, self.step)]
        columns += [self.end]
        for col in columns:
            df['SMA{}'.format(col)] = self.factory.create(SMA, period=col).run(symbol, df_quotes)['SMA']
        col_size = len(columns)
        df_comparison = df.lt(df_quotes.Close, axis=0)
        df_comparison['CountSMABelowPrice'] = round(100 * (df_comparison.filter(like='SMA') == True).astype(int).sum(axis=1) / col_size)
        df_comparison['CountSMAAbovePrice'] = round(100 * -(df_comparison.filter(like='SMA') == False).astype(int).sum(axis=1) / col_size)
        df['TrendStrength'] = df_comparison.CountSMABelowPrice + df_comparison.CountSMAAbovePrice

        self.add_direction(df, np.logical_and(df.TrendStrength >= 100, df.TrendStrength.shift(1) < 100),
                           np.logical_and(df.TrendStrength <= -100, df_quotes.High < df.filter(like='SMA').min(axis=1)))
        df = utils.round_df(df)
        return df


class BollingerBand(IndicatorRunner):
    def __init__(self, period=50, stdev=2):
        super().__init__(self.__class__.__name__, locals())
        self.period = period
        self.stdev = stdev

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        df = pd.DataFrame(index=df_quotes.index)
        df_sma = self.factory.create(SMA, period=self.period).run(symbol, df_quotes)
        df_stdev = self.factory.create(STDEV, period=self.period).run(symbol, df_quotes)
        df['Top'] = df_sma.SMA + (df_stdev.STDEV * self.stdev)
        df['Mid'] = df_sma.SMA
        df['Bottom'] = df_sma.SMA - (df_stdev.STDEV * self.stdev)

        self.add_direction(df, df_quotes.Close >= df.Top, df_quotes.High < df.Bottom)
        df = utils.round_df(df)
        return df


class RSI(IndicatorRunner):
    def __init__(self, period=20, field='Close'):
        super().__init__(self.__class__.__name__, locals())
        self.period = period
        self.field = field

    def SMMA(self, series, window=14):
        smma = series.ewm(
            ignore_na=False, alpha=1.0 / window,
            min_periods=0, adjust=True).mean()
        return smma

    def run(self, symbol, df_quotes, df_indicator=None):
        if self.is_updated(df_quotes, df_indicator):
            return df_indicator

        d = df_quotes[self.field].diff()
        df = pd.DataFrame()

        p_ema = self.SMMA((d + d.abs()) / 2, window=self.period)
        n_ema = self.SMMA((-d + d.abs()) / 2, window=self.period)

        df['RS'] = rs = p_ema / n_ema
        df['RSI'] = 100 - 100 / (1.0 + rs)

        self.add_direction(df, False, False)
        return df


class PickleIndicatorRunnerWrapper(object):
    def __init__(self, dir_path, runner):
        self.dir_path = dir_path
        self.runner = runner
        self.unique_name = runner.unique_name
        self.name = runner.name
        self.Columns = runner.Columns

    def get_save_path(self, symbol, df_quotes):
        return self.dir_path / '{}.{}'.format(symbol, config.PICKLE_EXTENSION)

    def update(self, symbol, df_quotes, df_indicator):
        if self.runner.is_updated(df_quotes, df_indicator):
            return df_indicator

        df = self.runner.run(symbol, df_quotes, df_indicator)
        save_path = self.get_save_path(symbol, df_quotes)
        utils.makedirs(save_path.parent)
        print('Saving {}'.format(save_path))
        df.to_pickle(save_path)
        return df

    def run(self, symbol, df_quotes, df_indicator=None):
        if os.path.exists(self.get_save_path(symbol, df_quotes)):
            return self.update(symbol, df_quotes, pd.read_pickle(self.get_save_path(symbol, df_quotes)))
        else:
            return self.update(symbol, df_quotes, df_indicator)


class DefaultIndicatorRunnerFactory(IndicatorRunnerFactory):
    def __init__(self, dir_path: Path):
        self.dir_path = dir_path

    def create(self, cls, *args, **kwargs):
        runner = cls(*args, **kwargs)
        runner.factory = DefaultIndicatorRunnerFactory(self.dir_path)
        save_path = self.dir_path / runner.unique_name
        return PickleIndicatorRunnerWrapper(save_path, runner)


class Attribute(entity.Attribute):
    def __init__(self, df_values):
        self.df_values = df_values

    def get_value(self, date=None, symbol=None, start=None):
        df = self.df_values.copy()
        if symbol is not None:
            df = df[symbol].dropna()

        if start is not None:
            df = df.loc[start:]
            if date is not None:
                df = df.loc[:date]
        elif date is not None:
            if date not in df.index:
                return None
            return df.loc[date]

        if symbol is not None:
            return df.values

        return df

    def get_indices(self, symbol=None, start=None, end=None):
        df = self.df_values.copy()
        df = df.loc[start:] if start is not None else df
        df = df.loc[:end] if end is not None else df
        if symbol is None:
            return df.index.values
        return df[symbol].dropna().index.values


class Indicator(entity.Indicator):
    def __init__(self, name, *attributes: Attribute):
        super().__init__(name, attributes)

    def __str__(self):
        return '{}: {}'.format(self.name, self.get_attribute_keys())

    def get_attribute(self, key):
        if type(self.attributes) == dict:
            if key in self.attributes.keys():
                return self.attributes[key]
        return None

    def get_attribute_keys(self):
        return self.attributes.keys()

    def get_indices(self, key=Direction.__name__, symbol=None, start=None, end=None):
        return self.get_attribute(key).get_indices(symbol, start=start, end=end)


class IndicatorFactory(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def create(self, runner_class, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def create_by_unique_name(self, unique_name):
        raise NotImplementedError


class DefaultIndicatorFactory(IndicatorFactory):
    def __init__(self, dir_path: Path, market: Market):
        self.dir_path = dir_path
        self.market = market
        self.runner_factory = DefaultIndicatorRunnerFactory(dir_path)

    def create_by_runner_instance(self, runner):
        indicator = Indicator(runner.unique_name, dict())
        print('Running {} for all symbols in the market...'.format(runner.unique_name))
        for symbol in self.market.get_symbols():
            df_quotes = self.market.get_quotes(symbol=symbol)
            if df_quotes.empty:
                continue
            df = runner.run(symbol, df_quotes)
            for col in df.columns:
                if not type(indicator.attributes) == dict:
                    indicator.attributes = dict()
                indicator.attributes[col] = indicator.get_attribute(col) or Attribute(pd.DataFrame())
                df_symbol = pd.DataFrame()
                df_symbol[symbol] = df[col]
                indicator.get_attribute(col).df_values = indicator.get_attribute(col).df_values.join(df_symbol, how='outer')
                indicator.get_attribute(col).df_values.sort_index()

        print('Finished running {} for all symbols in the market.'.format(runner.unique_name))
        return indicator

    def create_by_unique_name(self, unique_name):
        runner = self.runner_factory.create_by_unique_name(unique_name)
        return self.create_by_runner_instance(runner)

    def create(self, runner_class, *args, **kwargs):
        runner = self.runner_factory.create(runner_class, *args, **kwargs)
        return self.create_by_runner_instance(runner)


if __name__ == '__main__':
    INDICATORS_PATH = config.TEMP_PATH / 'indicators'
    HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'

    symbol = 'SM'
    market = pkl_to_market('pse', HISTORICAL_DATA_PATH)
    factory = DefaultIndicatorFactory(INDICATORS_PATH, market)
    macross = factory.create(MACross)
    fast = macross.get_attribute('FastSMA').get_value(symbol=symbol)
    print(fast)
