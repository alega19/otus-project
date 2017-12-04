import logging
import psycopg2
import time

from vkapi.config import DATABASE
from vkapi.config import DELAYS_BEFORE_RECONNECT_TO_DB


def _use_transaction_mode(fn):
    def wrapper(self, *args, **kwargs):
        if self._transaction_mode:
            return fn(self, *args, **kwargs)
        else:
            exc = None
            for delay in DELAYS_BEFORE_RECONNECT_TO_DB:
                try:
                    if self._conn is None:
                        self._connect()
                    result = fn(self, *args, **kwargs)
                    self._conn.commit()
                    return result
                except psycopg2.Error as err:
                    logging.warning(repr(err))
                    exc = err
                    self._rollback()
                    self.close()
                    time.sleep(delay)
            raise exc
    return wrapper


class Database:

    _conn = None

    @staticmethod
    def retry(fn):
        def wrapper(*args, **kwargs):
            for delay in DELAYS_BEFORE_RECONNECT_TO_DB:
                try:
                    return fn(*args, **kwargs)
                except psycopg2.Error as err:
                    logging.warning(repr(err))
                    time.sleep(delay)
            return fn(*args, **kwargs)
        return wrapper

    def __init__(self):
        self._transaction_mode = False
        if self._conn is None:
            self._connect()

    def _connect(self):
        self._conn = psycopg2.connect(host=DATABASE['host'], port=DATABASE['port'],
                                      dbname=DATABASE['dbname'], user=DATABASE['user'],
                                      password=DATABASE['password'])

    @_use_transaction_mode
    def execute(self, sql, params=None, handler=None):
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            if handler is not None:
                return [handler(row) for row in cursor]

    @_use_transaction_mode
    def executemany(self, sql, params_list):
        with self._conn.cursor() as cursor:
            cursor.executemany(sql, params_list)

    @classmethod
    def close(cls):
        if cls._conn is not None:
            try:
                cls._conn.close()
            except Exception:
                pass
            cls._conn = None

    def _rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def __enter__(self):
        self._transaction_mode = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._transaction_mode = False
        if exc_type is None:
            self._conn.commit()
        else:
            self._rollback()
