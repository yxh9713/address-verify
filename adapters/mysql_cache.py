import pymysql.err

from core.db import Database
from entities.address import Address
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MySQLCache:
    def __init__(self, database:Database):
        self.database = database

    def get(self, address: Address):
        conn = self.database.get_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT validated_id, address_one, address_two, city, state, zip, longitude, latitude, timezone, raw
                    FROM customers_validated
                    WHERE address_one = %s AND city = %s AND state = %s AND zip = %s
                    LIMIT 1
                    """,
                    (address.address_one, address.city, address.state, address.zip)
                )
                row = cursor.fetchone()

                if row is None:
                    return None

                return Address(
                    address_one = dict(row)["address_one"],
                    address_two = dict(row)["address_two"],
                    city = dict(row)["city"],
                    state = dict(row)["state"],
                    zip = dict(row)["zip"],
                    longitude = dict(row)["longitude"],
                    latitude = dict(row)["latitude"],
                    timezone = dict(row)["timezone"],
                    residential = dict(row)["raw"],
                    id = dict(row)["validated_id"]
                )

        except pymysql.err.Error as e:
            logger.error(f"mysql cache error: {e}")
            return None
