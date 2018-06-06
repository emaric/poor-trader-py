import traceback
from enum import Enum

import pandas as pd
import numpy as np
from matplotlib import pylab as plt
from matplotlib.finance import candlestick_ohlc
import matplotlib.dates as mdates

from poor_trader import config
from poor_trader.market import pkl_to_market
from poor_trader.screening import indicator

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

    ax2 = plt.subplot(312, sharex=ax)
    ax2.set_title('Drawdown : max drawdown={}'.format(df_equity_curve.Drawdown.min()), fontsize=18)
    ax2.bar(df_equity_curve.index, df_equity_curve.Drawdown, width=1, color='red')
    ax2.set_xticks(xticks)
    ax2.set_xticklabels(xlabels, fontsize=12)
    plt.xticks(rotation=90)

    ax3 = plt.subplot(313, sharex=ax)
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


def date2num(df):
    df.Date = df.Date.map(mdates.date2num)
    return df


def date2num_index(df):
    df.index = df.index.map(mdates.date2num)
    return df


def to_dohlc(df_quotes, start_date=None, end_date=None):
    df_ohlc = df_quotes.copy()
    if start_date is not None:
        df_ohlc = df_ohlc.loc[start_date:]
    if end_date is not None:
        df_ohlc = df_ohlc.loc[:end_date]
    df_ohlc = df_ohlc.reset_index()
    df_ohlc = df_ohlc.filter(items=["Date", "Open", "High", 'Low', "Close", "Volume"])
    return date2num(df_ohlc)


def ohlc_chart(df_dohlc, title='chart', save_path=None, open_close_line=None,
               volume=None, slsma=None, bollinger_band=None, donchian_channel=None, macd=None, trailing_stops=None, ma_cross=None, trend_strength_indicator=None):
    quotes = df_dohlc.values
    weekday_quotes = [tuple([i] + list(quote[1:])) for i, quote in enumerate(quotes)]

    ncharts = 1
    if volume is not None:
        ncharts += 1
    if trend_strength_indicator is not None:
        ncharts += 1
    if macd is not None:
        ncharts += 1

    fig = plt.figure(figsize=(20, 5 * ncharts))
    subplot_arg = ncharts * 100
    ax1 = plt.subplot(subplot_arg + 11)

    ls, rs = candlestick_ohlc(ax1, weekday_quotes, width=0.5, colorup='g', colordown='r', alpha=0.75)

    for r in rs:
        r.set_edgecolor('black')

    if bollinger_band is not None:
        ax1.plot(bollinger_band.Top.values, color='#60a0e0')
        ax1.plot(bollinger_band.Mid.values, color='#88c2fc')
        ax1.plot(bollinger_band.Bottom.values, color='#60a0e0')
        ax1.fill_between(range(len(bollinger_band)), bollinger_band.Top.values, bollinger_band.Bottom.values, color='#60a0e0', alpha=0.1)

    if donchian_channel is not None:
        ax1.plot(donchian_channel.High.values, color='#9160d1')
        ax1.plot(donchian_channel.Mid.values, color='#b38be8')
        ax1.plot(donchian_channel.Low.values, color='#9160d1')
        ax1.fill_between(range(len(donchian_channel)), donchian_channel.High.values, donchian_channel.Low.values, color='#9160d1', alpha=0.1)

    if trailing_stops is not None:
        ax1.plot(range(len(trailing_stops)), trailing_stops.BuyStops, 'rv', markersize=6)
        ax1.plot(range(len(trailing_stops)), trailing_stops.SellStops, 'g^', markersize=6)

    if ma_cross is not None:
        ax1.plot(ma_cross.FastSMA.values, linewidth=8, color='#3af8ff', alpha=0.6)
        ax1.plot(ma_cross.SlowSMA.values, linewidth=8, color='#bd3aff', alpha=0.6)

    if slsma is not None:
        ax1.plot(slsma.S_FastSMA.values, linewidth=2, color='#ff9900')
        ax1.plot(slsma.S_SlowSMA.values, linewidth=2, color='#935e0d')
        ax1.plot(slsma.L_FastSMA.values, linewidth=2, color='#ef7ca8')
        ax1.plot(slsma.L_SlowSMA.values, linewidth=2, color='#d63b74')

    ax1.set_ylabel("Price")
    ax1.set_title(title)
    xticks = range(0, len(weekday_quotes))
    ax1.set_xticks(xticks)
    xlabels = [mdates.num2date(quotes[index][0]).strftime('%Y-%m-%d %H:%M:%S') for index in ax1.get_xticks()]
    ax1.set_xticklabels(xlabels, fontsize=6.5)
    plt.xticks(rotation=90)

    if trend_strength_indicator is not None:
        trend_strength_indicator.reset_index()
        for col in trend_strength_indicator.filter(like='SMA').columns:
            ax1.plot(trend_strength_indicator[col].values, linewidth=0.5, color='r')
        ax2 = plt.subplot(subplot_arg + 12, sharex=ax1)
        ax2.plot(trend_strength_indicator.TrendStrength.values, linewidth=0.5, color='r')
        ax2.set_xticks(xticks)
        ax2.set_xticklabels(xlabels, fontsize=6.5)
        ax2.axhline(0, linewidth=0.5, color='black')
        ax2.set_ylabel('Trend Strength Indicator')
        plt.xticks(rotation=90)

    if macd is not None:
        macd = macd.reset_index()
        ax2 = plt.subplot(subplot_arg + (12 if trend_strength_indicator is None else 13), sharex=ax1)
        ax2.plot(macd.MACD.values, linewidth=0.5, color='blue')
        ax2.plot(macd.Signal.values, linewidth=0.5, color='red')
        ax2.bar(macd.index.values, macd.MACD.values - macd.Signal.values)
        ax2.set_xticks(xticks)
        ax2.set_xticklabels(xlabels, fontsize=6.5)
        ax2.axhline(0, linewidth=0.5, color='black')
        ax2.set_ylabel('MACD')
        plt.xticks(rotation=90)

    if volume is not None:
        ax2 = plt.subplot(subplot_arg + ncharts + 10, sharex=ax1)
        volume = volume.reset_index()
        df_dohlc = df_dohlc.reset_index()
        green_volume = df_dohlc.loc[df_dohlc['Open'] < df_dohlc['Close']]
        red_volume = df_dohlc.loc[df_dohlc['Open'] >= df_dohlc['Close']]
        ax2.bar(green_volume.index.values, green_volume.Volume.values, color='green', alpha=0.75)
        ax2.bar(red_volume.index.values, red_volume.Volume.values, color='red', alpha=0.75)
        ax2.fill_between(volume.index.values, volume.EMA.values, color='#469df4', alpha=0.8)
        ax2.set_xticks(xticks)
        ax2.set_xticklabels(xlabels, fontsize=6.5)
        ax2.set_ylabel('Volume')
        plt.xticks(rotation=90)

    if open_close_line is not None:
        buy_index = open_close_line.OpenIndex
        sell_index = open_close_line.CloseIndex
        buy = open_close_line.OpenPrice
        sell = open_close_line.ClosePrice
        marker_space = (max(df_dohlc.High.values) - min(df_dohlc.Low.values)) / 10

        ax1.plot((buy_index, sell_index), (buy, sell), 'o-', color='{}'.format('#ff00fa' if buy >= sell else '#21ff24'), linewidth=3, markersize=6)
        ax1.plot((buy_index), (buy - marker_space), color='#21ff24', marker='^', markersize=12, markeredgecolor='black')
        ax1.plot((sell_index), (sell + marker_space), color='#ff00fa', marker='v', markersize=12, markeredgecolor='black')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()

    plt.clf()
    plt.close(fig)


class TradeEnum(Enum):
    OPEN_INDEX = 'OpenIndex'
    CLOSE_INDEX = 'CloseIndex'
    OPEN_PRICE = 'OpenPrice'
    CLOSE_PRICE = 'ClosePrice'


if __name__ == '__main__':
    symbol = 'SM'
    pse_market = pkl_to_market('PSE', config.RESOURCES_PATH / 'historical_data.pkl')
    start = pd.to_datetime('2018-05-01')
    df_quotes = pse_market.get_quotes(symbol=symbol, start=start)
    df_donchian = indicator.DonchianChannel().run(symbol=symbol, df_quotes=pse_market.get_quotes(symbol=symbol))
    df_macd = indicator.MACD().run(symbol=symbol, df_quotes=pse_market.get_quotes(symbol=symbol))
    df_donchian = df_donchian.loc[start:]
    df_macd = df_macd.loc[start:]
    df_dohlc = to_dohlc(df_quotes)
    ohlc_chart(df_dohlc, donchian_channel=df_donchian, macd=df_macd)
