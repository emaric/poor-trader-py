# A study on security trading

Run tests:
```
python -m unittest discover
```


Run pycodestyle:
```
pycodestyle --ignore=E501 poor_trader/trading.py
pycodestyle --ignore=E501 poor_trader/pse.py
```


## Sample Backtest Results

#### Config 
|                      |                        | 
|----------------------|-----------------------:| 
| Trading System       |  ATR Channel Breakout  |
| Starting Balance     |  1000000.0             | 
| Start Date           |  2010-01-04            | 
| End Date             |  2018-04-30            | 
| Total Risk Per Trade |  Running Equity * 0.02 | 
| Unit Risk            |  Price * 0.2           | 



#### Trades Table
![Trades Table](docs/trades.csv "Trades Table")



#### Performance Table
|                        | Performance | 
|------------------------|------------:| 
| Number of Trading Days | 2033.0      | 
| Starting Capital       | 1000000.0   | 
| Ending Capital         | 4748459.72  | 
| Net Profit             | 3748459.72  | 
| Net Profit %           | 374.85      | 
| SQN                    | 2.46        | 
| Annualized Gain        | 0.21        | 
| Max Profit             | 1449662.77  | 
| Max Loss               | -209497.1   | 
| Number of Trades       | 440.0       | 
| Winning Trades         | 102.0       | 
| Losing Trades          | 338.0       | 
| Winning Trades %       | 23.18       | 
| Avg Profit/Loss        | 8519.23     | 
| Avg Profit             | 99991.02    | 
| Avg Loss               | -19084.69   | 
| Avg Profit/Loss %      | 4.61        | 
| Avg Profit %           | 41.52       | 
| Avg Loss %             | -6.53       | 
| Avg Bars Held          | 39.3        | 
| Avg Winning Bars Held  | 111.06      | 
| Avg Losing Bars Held   | 17.65       | 
| Max System Drawdown    | -2879129.44 | 
| Max System % Drawdown  | -39.1       | 
| Max Peak               | 7362822.11  | 
| Recovery Factor        | 95868.53    | 
| Profit Factor          | 1.58        | 
| Payoff Ratio           | 5.24        | 



#### Equity Curve
![Equity Curve Chart](docs/equity_curve_chart.png "Equity Curve Chart")
