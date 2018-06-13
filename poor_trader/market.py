import abc

import pandas as pd


class Market(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, symbols, name='Market'):
        self.name = name
        self.__symbols__ = symbols

    @abc.abstractmethod
    def get_dates(self, symbols=None, start=None, end=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_symbols(self, date=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_open(self, date=None, symbol=None, start=None, end=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_high(self, date=None, symbol=None, start=None, end=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_low(self, date=None, symbol=None, start=None, end=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_close(self, date=None, symbol=None, start=None, end=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_volume(self, date=None, symbol=None, start=None, end=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_quotes(self, date=None, symbol=None, start=None, end=None):
        raise NotImplementedError


class DataFrameMarket(Market):
    def __init__(self, df_historical_data, symbols=None, name='DataFrameMarket'):
        super().__init__(symbols, name)
        self.__df_historical_data__ = df_historical_data
        self.__symbols__ = symbols

    def get_dates(self, symbols=None, start=None, end=None):
        df = self.__df_historical_data__.copy()
        if start is not None:
            df = df.loc[start:]
        if end is not None:
            df = df.loc[:end]
        if symbols is None:
            return df.dropna(thresh=1).index.values
        else:
            return df.filter(regex='^({})_Date'.format('|'.join(symbols))).dropna(thresh=1).index.values

    def get_symbols(self, date=None):
        suffix = '_Date'
        if date is None:
            symbols = [_[:-len(suffix)] for _ in self.__df_historical_data__.filter(like=suffix).columns]
        else:
            symbols = [_[:-len(suffix)] for _ in self.__df_historical_data__.filter(like=suffix).loc[date:date].dropna(axis=1).columns]
        if self.__symbols__ is None or len(self.__symbols__) == 0:
            return symbols
        else:
            return [_ for _ in symbols if _ in self.__symbols__]

    def get_quotes(self, date=None, symbol=None, start=None, end=None):
        df = self.__df_historical_data__.copy()
        if start is not None:
            df = df.loc[start:]
        if end is not None:
            df = df.loc[:end]
        if date is not None:
            df = df.loc[date:date]
        if symbol is not None:
            df = df.filter(regex='^{}_'.format(symbol))
            df.columns = [_.replace('{}_'.format(symbol), '') for _ in df.columns]
            df = df.dropna()
        return df

    def __get_value_by_column__(self, column, date=None, symbol=None, start=None, end=None):
        df = self.get_quotes(date=date, symbol=symbol, start=start, end=end).filter(like=column)
        if len(df.columns) == 1 and len(df.index.values) == 1:
            return df.iloc[0][column]
        return df

    def get_open(self, date=None, symbol=None, start=None, end=None):
        return self.__get_value_by_column__('Open', date=date, symbol=symbol, start=start, end=end)

    def get_high(self, date=None, symbol=None, start=None, end=None):
        return self.__get_value_by_column__('High', date=date, symbol=symbol, start=start, end=end)

    def get_low(self, date=None, symbol=None, start=None, end=None):
        return self.__get_value_by_column__('Low', date=date, symbol=symbol, start=start, end=end)

    def get_close(self, date=None, symbol=None, start=None, end=None):
        return self.__get_value_by_column__('Close', date=date, symbol=symbol, start=start, end=end)

    def get_volume(self, date=None, symbol=None, start=None, end=None):
        return self.__get_value_by_column__('Volume', date=date, symbol=symbol, start=start, end=end)


def csv_to_market(name, csv_path, symbols=None):
    df_historical_data = pd.read_csv(csv_path, parse_dates=True, index_col=0)
    return DataFrameMarket(df_historical_data=df_historical_data, name=name, symbols=symbols)


def pkl_to_market(name, pkl_path, symbols=None):
    df_historical_data = pd.read_pickle(pkl_path)
    return DataFrameMarket(df_historical_data=df_historical_data, name=name, symbols=symbols)
