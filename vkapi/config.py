import json
from os.path import join, dirname, abspath


with open(join(dirname(abspath(__file__)), '..', 'secrets.json')) as _fd:
    _SECRETS = json.loads(_fd.read())


DATABASE = {
    'host': _SECRETS['db_host'],
    'port': _SECRETS['db_port'],
    'dbname': _SECRETS['db_name'],
    'user': _SECRETS['db_user'],
    'password': _SECRETS['db_pass']
}

WORKERS_PER_TOKEN = 1
REQUEST_DELAY_PER_TOKEN = 0.5  # in seconds
REQUEST_TIMEOUT = 120  # in seconds
TRIES_PER_TASK = 2
DELAYS_BEFORE_RECONNECT_TO_DB = range(0, 10)  # in seconds
