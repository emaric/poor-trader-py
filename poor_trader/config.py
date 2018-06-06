import os
from path import Path


class Config(object):
    def __init__(self, name='_config'):
        self.name = name


PICKLE_EXTENSION = 'pkl'

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

ROOT_PATH = Path(os.path.dirname(__file__)).parent

RESOURCES_PATH = ROOT_PATH / 'resources'

TEST_RESOURCES_PATH = (ROOT_PATH / 'tests') / 'resources'

TEMP_PATH = ROOT_PATH.parent / 'poor-trader-tmp'

TEST_TEMP_PATH = TEST_RESOURCES_PATH / 'tmp'

BOARD_LOT_CSV_PATH = RESOURCES_PATH / 'boardlot.csv'
