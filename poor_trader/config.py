import datetime
import os
from path import Path


class Config(object):
    def __init__(self, name='_config'):
        self.name = name


PICKLE_EXTENSION = 'pkl'

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

DATETIME_FORMAT_FILENAME_SAFE = '%Y-%m-%d_%H%M%S'

DATE_FORMAT = '%Y-%m-%d'

ROOT_PATH = Path(os.path.dirname(__file__)).parent

RESOURCES_PATH = ROOT_PATH / 'resources'

TEST_RESOURCES_PATH = (ROOT_PATH / 'tests') / 'resources'

TEMP_PATH = ROOT_PATH.parent / 'poor-trader-tmp'

TEST_TEMP_PATH = TEST_RESOURCES_PATH / 'tmp'

BOARD_LOT_CSV_PATH = RESOURCES_PATH / 'boardlot.csv'

APP_DIR_NAME = 'PoorTrader'

BACKTESTING_DIR_NAME = 'Backtest'

EQUITY_CURVE_FILENAME = 'equity_curve.csv'

TRANSACTIONS_FILENAME = 'transactions.csv'


def generate_backtesting_results_dir_path():
    datetime_tag = datetime.datetime.now().strftime(DATETIME_FORMAT_FILENAME_SAFE)
    return Path(os.path.expanduser('~/' + APP_DIR_NAME)) / '{}_{}'.format(BACKTESTING_DIR_NAME, datetime_tag)
