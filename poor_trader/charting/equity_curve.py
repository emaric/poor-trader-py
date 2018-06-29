import datetime
import traceback
from enum import Enum

import pandas as pd
import numpy as np
from matplotlib import pylab as plt

from poor_trader import config
from poor_trader.backtesting.equity_curve import DefaultEquityCurve
from poor_trader.charting.entity import ChartObject

plt.style.use('ggplot')

EQUITY_COLOR = 'limegreen'
CASH_COLOR = 'green'
DRAWDOWN_COLOR = 'red'
DRAWDOWN_PERCENT_COLOR = 'red'


class EquityCurveKey(Enum):
    EQUITY = 'Equity'
    CASH = 'Cash'
    DRAWDOWN = 'Drawdown'
    DRAWDOWN_PERCENT = 'DrawdownPercent'


class EquityCurveChartObject(ChartObject):
    def __init__(self, equity=100000.0, cash=100000.0, drawdown=0.0, drawdown_percent=0.0):
        super().__init__(EquityCurveKey, equity, cash, drawdown, drawdown_percent)


class EquityCurveChart(object):
    def __init__(self, indices=list(), equity_curve_chart_object=list(), index_labels=list()):
        self.indices = indices
        self.equity_curve_chart_object = equity_curve_chart_object
        self.index_labels = indices if len(index_labels) <= 0 else index_labels


def create(data: EquityCurveChart,
           equity_cash_title='Equity Curve',
           drawdown_title='Drawdown',
           drawdown_pct_title='Drawdown %',
           fpath=None):

    indices = data.indices
    equity = [_[EquityCurveKey.EQUITY.value] for _ in data.equity_curve_chart_object]
    cash = [_[EquityCurveKey.CASH.value] for _ in data.equity_curve_chart_object]
    drawdown = [_[EquityCurveKey.DRAWDOWN.value] for _ in data.equity_curve_chart_object]
    drawdown_pct = [_[EquityCurveKey.DRAWDOWN_PERCENT.value] for _ in data.equity_curve_chart_object]

    xaxis = range(len(indices))
    space = 15
    xticks = np.linspace(0, len(indices) - 1, space if len(indices) >= space else len(indices), dtype=int)
    xlabels = [str(data.index_labels[i]) for i in xticks]

    title_fontsize = 12
    xlabels_fontsize = 8
    xticks_rotation = 10

    fig = plt.figure(figsize=(30, 30))

    subplot_start = 311
    ax = plt.subplot(subplot_start)
    ax.set_title(equity_cash_title, fontsize=title_fontsize)
    ax.bar(xaxis, equity, width=1, color=EQUITY_COLOR)
    ax.bar(xaxis, cash, width=1, color=CASH_COLOR)
    ax.set_yticklabels(['{:.4f}'.format(y) for y in ax.get_yticks()])
    ax.set_xticks(xticks)
    ax.set_xticklabels([' ' for _ in xlabels], fontsize=xlabels_fontsize)
    plt.xticks(rotation=xticks_rotation)

    for values, title, color, label_format in zip([drawdown,        drawdown_pct],
                                                  [drawdown_title,  drawdown_pct_title],
                                                  [DRAWDOWN_COLOR,  DRAWDOWN_PERCENT_COLOR],
                                                  ['{:.4f}',        '{:3.2f}%']):
        subplot_start += 1
        sub_ax = plt.subplot(subplot_start, sharex=ax)
        sub_ax.set_title(title, fontsize=title_fontsize)
        sub_ax.bar(xaxis, values, width=1, color=color)
        sub_ax.set_yticklabels([label_format.format(y) for y in sub_ax.get_yticks()])
        sub_ax.set_xticks(xticks)
        sub_ax.set_xticklabels(xlabels, fontsize=xlabels_fontsize)
        plt.xticks(rotation=xticks_rotation)

    if fpath:
        try:
            plt.savefig(fpath)
            plt.clf()
            plt.close(fig)
        except RuntimeError:
            print('Error charting {}'.format(title))
            print(traceback.print_exc())
    else:
        plt.show()


def read_equity_curve_csv(path):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return DefaultEquityCurve(df=df)


def create_equity_curve_chart(equity_curve: DefaultEquityCurve):
    chart_objects = [EquityCurveChartObject(equity=equity_curve.get_equity(date),
                                            cash=equity_curve.get_cash(date),
                                            drawdown=equity_curve.get_drawdown(date),
                                            drawdown_percent=equity_curve.get_drawdown_percent(date))
             for date in equity_curve.get_dates()]
    index_labels = [date.strftime(config.DATETIME_FORMAT) for date in equity_curve.get_dates()]
    return EquityCurveChart(indices=equity_curve.get_dates(), equity_curve_chart_object=chart_objects, index_labels=index_labels)


def csv_to_chart(equity_curve_csv_path, save_path=None):
    equity_curve = read_equity_curve_csv(equity_curve_csv_path)
    equity_curve_chart = create_equity_curve_chart(equity_curve)
    create(equity_curve_chart, fpath=save_path)


if __name__ == '__main__':
    indices = [pd.to_datetime('2017-01-01') + datetime.timedelta(days=i) for i in range(500)]
    index_labels = [d.strftime(config.DATETIME_FORMAT) for d in indices]

    equity_data = [np.random.randint(10, 15) * i for i in range(1, len(indices) + 1)]
    cash = [np.random.randint(1, 5) * i for i in range(1, len(indices) + 1)]
    dd = pd.Series(equity_data).expanding().apply(lambda e: -(e.max() - e[-1]))
    dd_pct = pd.Series(equity_data).expanding().apply(lambda e: -100 * ((e.max() - e[-1]) / e.max()))

    items = [EquityCurveChartObject(equity_data[i], cash[i], dd[i], dd_pct[i]) for i in range(len(indices))]
    test_data = EquityCurveChart(indices=indices, equity_curve_chart_object=items, index_labels=index_labels)
    create(test_data)
