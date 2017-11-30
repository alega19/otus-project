DATABASE = {
    'host': '127.0.0.1',
    'port': 5432,
    'dbname': 'ovk',
    'user': 'postgres',
    'password': 'postgres'
}

WORKERS_PER_TOKEN = 1
REQUEST_DELAY_PER_TOKEN = 0.5  # in seconds
REQUEST_TIMEOUT = 120  # in seconds
TRIES_PER_TASK = 2
DELAYS_BEFORE_RECONNECT_TO_DB = range(0, 10)  # in seconds
