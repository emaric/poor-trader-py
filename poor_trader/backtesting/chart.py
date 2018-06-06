import traceback
import pandas as pd
import numpy as np
from matplotlib import pylab as plt

plt.style.use('ggplot')


def generate_equity_chart(df_equity_curve, fpath, title='Equity Curve'):
    df_equity_curve['Date'] = df_equity_curve.index
    df_equity_curve = df_equity_curve.reset_index()
    xticks = np.linspace(0, len(df_equity_curve.index.values) - 1,
                         20 if len(df_equity_curve.index.values) >= 20 else (len(df_equity_curve.index.values)))
    xlabels = [pd.to_datetime(df_equity_curve.Date.values[int(index)]).strftime('%Y-%m-%d') for index in
               xticks]

    fig = plt.figure(figsize=(30, 30))

    ax = plt.subplot(311)
    ax.set_title(
        'Equity Curve : cash={}, equity={}'.format(df_equity_curve.Cash.values[-1], df_equity_curve.Equity.values[-1]),
        fontsize=18)
    ax.bar(df_equity_curve.index, df_equity_curve.Equity, width=1, color='limegreen')
    ax.bar(df_equity_curve.index, df_equity_curve.Cash, width=1, color='green')
    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels, fontsize=12)
    plt.xticks(rotation=90)

    ax2 = plt.subplot(312)
    ax2.set_title('Drawdown : max drawdown={}'.format(df_equity_curve.Drawdown.min()), fontsize=18)
    ax2.bar(df_equity_curve.index, df_equity_curve.Drawdown, width=1, color='red')
    ax2.set_xticks(xticks)
    ax2.set_xticklabels(xlabels, fontsize=12)
    plt.xticks(rotation=90)

    ax3 = plt.subplot(313)
    ax3.set_title('Drawdown % : max drawdown %={}%'.format(df_equity_curve.DrawdownPercent.min()), fontsize=18)
    ax3.bar(df_equity_curve.index, df_equity_curve.DrawdownPercent, width=1, color='red')
    ax3.set_yticklabels(['{:3.2f}%'.format(y) for y in ax3.get_yticks()])
    ax3.set_xticks(xticks)
    ax3.set_xticklabels(xlabels, fontsize=12)
    plt.xticks(rotation=90)

    if fpath:
        try:
            plt.savefig(fpath)
        except:
            print('Error charting {}'.format(title))
            print(traceback.print_exc())
    else:
        plt.show()
    plt.clf()
    plt.close(fig)
