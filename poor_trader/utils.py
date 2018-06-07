import os
import traceback

import pandas as pd

from poor_trader import config


def makedirs(path):
    if not os.path.exists(path):
        print('Creating directory', path)
        os.makedirs(path)


def load_equity_table(fpath):
    if os.path.exists(fpath):
        df = pd.read_csv(fpath, index_col=0, parse_dates=True)
        return df


def roundn(n, places=4):
    try:
        return float('%.{}f'.format(places) % n)
    except:
        return n


def _round(nseries, places=4):
    try:
        return pd.Series([roundn(n, places) for n in nseries], nseries.index)
    except:
        return nseries


def round_df(df, places=4):
    return df.apply(lambda x : _round(x, places))


def rindex(mylist, myvalue):
    return len(mylist) - mylist[::-1].index(myvalue) - 1


def quotes_range(df_quotes):
    if len(df_quotes.index.values) == 0:
        return 'None'
    start = df_quotes.index.values[0]
    end = df_quotes.index.values[-1]
    try:
        start = pd.to_datetime(start)
        end = pd.to_datetime(end)
        dateformat = '%Y%m%d'
        return '{}_to_{}'.format(start.strftime(dateformat), end.strftime(dateformat))
    except:
        return '{}_to_{}'.format(start, end)


def load_boardlot(boardlot_csv_path):
    df = pd.read_csv(boardlot_csv_path)
    df.index = df.StartPrice.values
    return df


def boardlot(price):
    try:
        df_boardlot = load_boardlot(config.BOARD_LOT_CSV_PATH)
        return int(df_boardlot.loc[df_boardlot.StartPrice <= price].iloc[-1].BoardLot)
    except:
        return 0


def to_enum(series, enum_class):
    return series.apply(lambda v: enum_class[v.replace(enum_class.__name__ + '.', '')])
