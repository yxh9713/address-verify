import logging
import pymysql
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from core.config import Config

logger = logging.getLogger(__name__)

class Database:
    # constructor
    def __init__(self, config: Config):
        self._host = config.mysql_host
        self._port = config.mysql_port
        self._user = config.mysql_user
        self._password = config.mysql_password
        self._database = config.mysql_db
        self._connection: pymysql.connections.Connection | None = None

    def get_connection(self) ->  pymysql.connections.Connection:
        if self._connection is None:
            self._connection = self._connect()
        else:
            try:
                self._connection.ping(reconnect=True)
            except pymysql.err.Error:
                self._connection = self._connect()

        assert self._connection is not None
        return self._connection

    def _connect(self) -> pymysql.connections.Connection:
        return pymysql.connect(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            database=self._database,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    def test_connection(self) -> bool:
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return True
        except pymysql.err.Error as e:
            logger.error("MySQL connection test failed: %s", e)
            return False

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            except pymysql.err.Error:
                pass
            self._connection = None