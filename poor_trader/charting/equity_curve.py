import datetime
import traceback

import pandas as pd
import numpy as np
from matplotlib import pylab as plt

from poor_trader import config
from poor_trader.charting import entity

plt.style.use('ggplot')

EQUITY_COLOR = 'limegreen'
CASH_COLOR = 'green'
DRAWDOWN_COLOR = 'red'
DRAWDOWN_PERCENT_COLOR = 'red'


def create(data: entity.EquityCurveChart,
           equity_cash_title='Equity Curve',
           drawdown_title='Drawdown',
           drawdown_pct_title='Drawdown %',
           fpath=None):
    indices = data.indices
    equity = [_.Equity for _ in data.equity_curve_items]
    cash = [_.Cash for _ in data.equity_curve_items]
    drawdown = [_.Drawdown for _ in data.equity_curve_items]
    drawdown_pct = [_.DrawdownPercent for _ in data.equity_curve_items]

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
        except RuntimeError:
            print('Error charting {}'.format(title))
            print(traceback.print_exc())
    else:
        plt.show()
    plt.clf()
    plt.close(fig)


if __name__ == '__main__':
    indices = [pd.to_datetime('2017-01-01') + datetime.timedelta(days=i) for i in range(500)]
    index_labels = [d.strftime(config.DATETIME_FORMAT) for d in indices]

    equity_data = [np.random.randint(10, 15) * i for i in range(1, len(indices) + 1)]
    cash = [np.random.randint(1, 5) * i for i in range(1, len(indices) + 1)]
    dd = pd.Series(equity_data).expanding().apply(lambda e: -(e.max() - e[-1]))
    dd_pct = pd.Series(equity_data).expanding().apply(lambda e: -100 * ((e.max() - e[-1]) / e.max()))

    items = [entity.EquityCurveItem(equity_data[i], cash[i], dd[i], dd_pct[i]) for i in range(len(indices))]
    test_data = entity.EquityCurveChart(indices=indices, equity_curve_items=items, index_labels=index_labels)
    create(test_data)
