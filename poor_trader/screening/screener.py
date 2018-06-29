import numpy as np
import pandas as pd
from poor_trader import market, config
from poor_trader.screening import indicator
from poor_trader.screening.entity import Direction, Screener


class DataFrameScreener(Screener):
    def __init__(self, _market: market.DataFrameMarket, indicators_path):
        self.market = _market
        self.indicators_path = indicators_path

    def get_minimum_trading_periods(self):
        factory = indicator.IndicatorRunnerFactory()
        runner_classes = indicator.IndicatorRunner.__subclasses__()
        runners = [factory.create(runner_class) for runner_class in runner_classes]
        attribute_values = [runner.__dict__.values() for runner in runners]
        int_attribute_values = []
        for attribute_value in attribute_values:
            int_attribute_values.extend([_ for _ in attribute_value if isinstance(_, int)])
        return np.max(int_attribute_values)

    def trim_market(self, start=None, end=None):
        if start is not None:
            raise NotImplementedError
        if end is not None:
            raise NotImplementedError
        min_bars = self.get_minimum_trading_periods() + 5
        return market.DataFrameMarket(self.market.__df_historical_data__.iloc[-min_bars:])

    def create_indicators(self, start=None, end=None):
        indicators = []
        factory = indicator.DefaultIndicatorFactory(self.indicators_path, self.trim_market(start, end))
        runner_classes = indicator.IndicatorRunner.__subclasses__()
        for runner_class in runner_classes:
            indicators.append(factory.create(runner_class))
        return indicators

    @staticmethod
    def collect_symbols(s_attribute_values, direction):
        df = pd.DataFrame()
        df[Direction.__name__] = s_attribute_values
        df = df[df[Direction.__name__] == direction]
        return df.index.values

    def scan(self, start=None, end=None):
        indicators = self.create_indicators(start, end)
        df_long = pd.DataFrame()
        df_short = pd.DataFrame()
        for _indicator in indicators:
            df_values = _indicator.get_attribute(Direction.__name__).get_value()[-5:]
            df_long[_indicator.name] = df_values.apply(lambda s_values: ' '.join(self.collect_symbols(s_values, Direction.LONG)), axis=1)
            df_short[_indicator.name] = df_values.apply(lambda s_values: ' '.join(self.collect_symbols(s_values, Direction.SHORT)), axis=1)
        return df_long, df_short

    @staticmethod
    def print(tag, df_scan_result):
        for index in df_scan_result.index.values:
            print('-----------------------------------------------------------------------------------------')
            for col in df_scan_result.columns:
                symbols = df_scan_result.loc[index][col].split()
                if len(symbols) > 0:
                    print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
                    print(tag, ' -- ', pd.to_datetime(index).strftime(config.DATETIME_FORMAT), ' -- ', col.upper())
                    print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
                    width = 10
                    matrix = [symbols[i:i+width] for i in range(0, len(symbols), width)]
                    for line in matrix:
                        print(' '.join(['{:<7}' for _ in range(len(line))]).format(*line))
                    print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
                    print()
                    print()
            print('-----------------------------------------------------------------------------------------')


if __name__ == '__main__':
    INDICATORS_PATH = (config.TEMP_PATH / 'screener') / 'indicators'
    HISTORICAL_DATA_PATH = config.RESOURCES_PATH / 'historical_data.pkl'
    print('INDICATOR_PATH', INDICATORS_PATH)

    screener = DataFrameScreener(market.pkl_to_market('PSE', HISTORICAL_DATA_PATH), INDICATORS_PATH)
    df_long, df_short = screener.scan()

    re_indicators = '^(atr_channel|donchian|bollinger|trend_strength|trailing_stops|ma_cross)_'
    screener.print('SHORT', df_short.filter(regex=re_indicators))
    screener.print('LONG', df_long.filter(regex=re_indicators))
