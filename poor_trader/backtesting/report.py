
import datetime
import numpy as np
import pandas as pd
from poor_trader.backtesting import chart
from poor_trader import utils

TRADE_DAYS_PER_YEAR = 244


def SQN(df_trades):
    """
    System Quality Number = (Expectancy / Standard Deviation R) * sqrt(Number of Trades)
    :param df_trades:
    :return:
    """
    try:
        sqn = (df_trades.LastRMultiple.mean() / df_trades.LastRMultiple.std()) * np.sqrt(len(df_trades.index.values))
        return np.round(sqn, 2)
    except:
        return 0


def drawdown(equities):
    return -np.round(equities.max() - equities[-1], 4)


def drawdown_pct(equities):
    dd = equities[-1] - equities.max()
    dd_pct = 100 * dd / equities.max()
    return np.round(dd_pct, 2)


def exposure(open_trades, portfolio_equity):
    return open_trades['LastValue'].apply(lambda last_value: 100 * last_value / portfolio_equity)


def exposure_pct(df_trades, df_backtest, starting_capital):
    df = pd.DataFrame()
    def calc(row):
        date = row.name
        cur_trades = backtest.update_open_trades_last_value(df_trades[df_trades['StartDate'] <= date], date=date)
        portfolio_equity = starting_capital + cur_trades['LastPnL'].sum()
        open_trades = cur_trades[pd.isnull(cur_trades['EndDate'])]
        return open_trades['LastPnL'].sum() / portfolio_equity
    df['Exposure'] = df_backtest.apply(calc, axis=1)
    return df['Exposure']

def avg_expectancy(df_trades):
    return df_trades['LastPnL'].mean()


def avg_expectancy_pct(df_trades):
    expectancy_pct = 100 * df_trades['LastPnL'] / df_trades['BuyValue']
    return expectancy_pct.mean()


def avg_bars_held(df_backtest, df_trades):
    bars_held = df_trades.apply(lambda trade: len(df_backtest.loc[pd.to_datetime(trade['StartDate']):pd.to_datetime(trade['LastRecordDate'])].index.values), axis=1)
    bars_held = bars_held.dropna()
    if bars_held.empty:
        return 0
    return np.round(bars_held.mean(), 2)


def max_drawdown(df_backtest):
    return df_backtest['Equity'].expanding().apply(drawdown).min()


def max_pct_drawdown(df_backtest):
    return df_backtest['Equity'].expanding().apply(drawdown_pct).min()


def ulcer_index(df_backtest):
    df_dd = df_backtest['Equity'].expanding().apply(drawdown_pct)
    squared_dd = df_dd * df_dd
    return np.sqrt(squared_dd.sum()) / squared_dd.count()


def performance_data(starting_capital, df_backtest, df_trades, index='Performance'):
    df = pd.DataFrame()

    equities = df_backtest['Equity'].values
    years = len(equities) / TRADE_DAYS_PER_YEAR

    ending_capital = df_backtest['Equity'].values[-1]
    net_profit = ending_capital - starting_capital
    net_profit_pct = 100 * net_profit / starting_capital
    annualized_gain = ((ending_capital/starting_capital)**(1/years) - 1)
    max_system_dd = max_drawdown(df_backtest)
    max_system_pct_dd = max_pct_drawdown(df_backtest)
    max_peak = df_backtest.Equity.max()
    df_winning_trades = df_trades[df_trades['LastPnL'] > 0]
    df_losing_trades = df_trades[df_trades['LastPnL'] <= 0]
    ui = ulcer_index(df_backtest)
    avg_bars_held_value = avg_bars_held(df_backtest, df_trades)
    avg_expectancy_pct_value = avg_expectancy_pct(df_trades)
    risk_free_rate = 0.01

    df.loc[index, 'Number of Trading Days'] = df_backtest.Equity.count()
    df.loc[index, 'Starting Capital'] = starting_capital
    df.loc[index, 'Ending Capital'] = ending_capital
    df.loc[index, 'Net Profit'] = net_profit
    df.loc[index, 'Net Profit %'] = net_profit_pct

    df.loc[index, 'SQN'] = SQN(df_trades)
    df.loc[index, 'Annualized Gain'] = annualized_gain

    df.loc[index, 'Max Profit'] = df_trades.LastPnL.max()
    df.loc[index, 'Max Loss'] = df_trades.LastPnL.min()

    df.loc[index, 'Number of Trades'] = len(df_trades.index.values)
    df.loc[index, 'Winning Trades'] = len(df_winning_trades.index.values)
    df.loc[index, 'Losing Trades'] = len(df_losing_trades.index.values)
    try:
        df.loc[index, 'Winning Trades %'] = np.round(100 * (len(df_winning_trades.index.values) / len(df_trades.index.values)), 2)
    except:
        df.loc[index, 'Winning Trades %'] = 0

    df.loc[index, 'Avg Profit/Loss'] = avg_expectancy(df_trades)
    df.loc[index, 'Avg Profit'] = avg_expectancy(df_winning_trades)
    df.loc[index, 'Avg Loss'] = avg_expectancy(df_losing_trades)

    df.loc[index, 'Avg Profit/Loss %'] = avg_expectancy_pct_value
    df.loc[index, 'Avg Profit %'] = avg_expectancy_pct(df_winning_trades)
    df.loc[index, 'Avg Loss %'] = avg_expectancy_pct(df_losing_trades)

    df.loc[index, 'Avg Bars Held'] = avg_bars_held_value
    df.loc[index, 'Avg Winning Bars Held'] = avg_bars_held(df_backtest, df_winning_trades)
    df.loc[index, 'Avg Losing Bars Held'] = avg_bars_held(df_backtest, df_losing_trades)

    df.loc[index, 'Max System Drawdown'] = max_system_dd
    df.loc[index, 'Max System % Drawdown'] = max_system_pct_dd
    df.loc[index, 'Max Peak'] = max_peak

    df.loc[index, 'Recovery Factor'] = net_profit / abs(max_system_pct_dd)
    try:
        df.loc[index, 'Profit Factor'] = df_winning_trades['LastPnL'].sum() / abs(df_losing_trades['LastPnL'].sum())
    except:
        df.loc[index, 'Profit Factor'] = 0.0
    df.loc[index, 'Payoff Ratio'] = df_winning_trades['LastPnL'].mean() / abs(df_losing_trades['LastPnL'].mean())

    return utils.round_df(df, places=2)


def generate_equity_curve(df_trades, starting_balance, historical_data, selling_fees_method=None, start_date=None, end_date=None):
    df_trades['StartDate'] = pd.to_datetime(df_trades['StartDate'])
    df_trades['EndDate'] = pd.to_datetime(df_trades['EndDate'])
    df_trades['LastRecordDate'] = pd.to_datetime(df_trades['LastRecordDate'])

    if start_date is None:
        start_date = df_trades.StartDate.min()
    if end_date is None:
        end_date = df_trades.LastRecordDate.max()

    start_date = pd.to_datetime(start_date)
    df_quotes = historical_data.copy()
    if start_date:
        df_quotes = df_quotes.loc[start_date:]
    if end_date:
        df_quotes = df_quotes.loc[:end_date]

    df = pd.DataFrame()
    for index in df_quotes.index.values.astype('datetime64[D]'):
        date = pd.to_datetime(index)
        cash = starting_balance - df_trades.loc[df_trades['StartDate'] <= date].BuyValue.sum()
        cash_value = cash + df_trades.loc[df_trades['EndDate'] <= date].SellValue.dropna().sum()

        current_value = 0
        open_trades = df_trades.loc[df_trades['StartDate'] <= date]
        open_trades = open_trades[(open_trades['EndDate'] > date) | (pd.isnull(open_trades['EndDate']))]
        for open_trade_index in open_trades.index:
            open_trade = open_trades.loc[open_trade_index]
            prices = df_quotes.loc[:date]['{}_Close'.format(open_trade.Symbol)].dropna().values
            price = prices[-1] if len(prices) > 0 else open_trade['LastPrice']
            shares = open_trade.Shares
            value = price * shares
            if selling_fees_method is not None:
                value = price * shares - selling_fees_method(price, shares)
            current_value += value

        equity_value = cash_value + current_value
        index = pd.to_datetime(index)
        df.loc[index, 'Cash'] = cash_value
        df.loc[index, 'Equity'] = equity_value
        exposure_pct = 100 * current_value / equity_value
        df.loc[index, 'Exposure %'] = exposure_pct

    if not df.empty:
        before_start_date = pd.to_datetime(df.index.values[0]) - datetime.timedelta(days=1)
        df.loc[before_start_date, 'Cash'] = starting_balance
        df.loc[before_start_date, 'Equity'] = starting_balance
        df.loc[before_start_date, 'Exposure %'] = 0.0
        df = df.sort_index()

        df['Drawdown'] = df['Equity'].expanding().apply(drawdown)
        df['DrawdownPercent'] = df['Equity'].expanding().apply(drawdown_pct)

        df = utils.round_df(df)
    return df

def generate_report(df_trades, starting_balance, historical_data, output_dir_path, calculate_selling_fees_method=None):
    df_equity_curve = generate_equity_curve(df_trades=df_trades, starting_balance=starting_balance, historical_data=historical_data, selling_fees_method=calculate_selling_fees_method)
    if not df_equity_curve.empty:
        df_equity_curve.to_csv(output_dir_path / 'equity_curve.csv')
        chart.generate_equity_chart(df_equity_curve=df_equity_curve, fpath=output_dir_path / 'equity_curve_chart.pdf')

        df = pd.DataFrame()
        df['Performance'] = performance_data(starting_balance, df_equity_curve, df_trades).iloc[0]
        df.to_csv(output_dir_path / 'report.csv')


