from typing import List

import pymysql
from core.db import Database
from entities.shipment import Address, Shipment
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ShipmentGateway:
    def __init__(self, database: Database, look_back_days: int = 3):
        self.database = database
        self.look_back_days = look_back_days

    def get_shipments(self, worker_id: int):
        conn = self.database.get_connection()

        try:
            # Back Pressure: rows this worker already has locked
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM raw_shipments
                    WHERE updated_at > (NOW() - INTERVAL %s DAY)
                    AND (validator_thread = %s AND validator_locked > (NOW() - INTERVAL %s DAY))
                    ORDER BY updated_at ASC
                    """,
                    (self.look_back_days, worker_id, self.look_back_days),
                )

                # if rows, process and return
                if cursor.rowcount:
                    rows = cursor.fetchall()
                    shipments = self._map_rows_to_shipments(rows)
                    return shipments

                # No locked rows -> claim a fresh batch
                cursor.execute(
                    """
                    UPDATE raw_shipments
                    SET validator_thread = %s, validator_locked = NOW()
                    WHERE validator_thread IS NULL
                    AND validator_locked IS NULL
                    AND (is_validated IS NULL OR is_validated = 0 AND validation_failed = 0)
                    AND updated_at >= (NOW() - INTERVAL %s DAY)
                    AND company_id NOT IN (24, 25, 75, 61)
                    LIMIT 1000
                    """,
                    (worker_id, self.look_back_days),
                )

                if cursor.rowcount == 0:
                    return []

                cursor.execute(
                    """
                    SELECT * FROM raw_shipments
                    WHERE validator_thread = %s
                    AND validator_locked >= (NOW() - INTERVAL %s DAY)
                    """,
                    (worker_id, self.look_back_days),
                )
                rows = cursor.fetchall()

                return self._map_rows_to_shipments(rows)

        except pymysql.err.Error as e:
            logger.error("get_shipments failed: %s", e)
            return []

    def mark_failed(self, raw_id: int):
        logger.error(f"raw shipment {raw_id} mark failed")
        conn = self.database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE raw_shipments
                    SET validation_failed = 1,
                        validator_locked = NULL,
                        validator_thread = NULL,
                        is_validated = 0
                    WHERE raw_id = %s            
                    """,
                    (raw_id,)
                )
        except pymysql.err.Error as e:
            logger.error(f"{raw_id} mark failed: {e}")

    def update_raw_shipment(self, raw_id: int, validated_id: int):
        conn = self.database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE raw_shipments
                    SET validated_id = %s, validator_locked = NULL, validator_thread = NULL, is_validated = 1, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (validated_id, raw_id),
                )
        except pymysql.err.Error as e:
            logger.error(f"{raw_id} update raw_shipments failed: {e}")

    def save_address(self, raw_id: int, address: Address):
        if address.valid:
            if address.id is None:
                self._save_validated_address(raw_id, address)
            else:
                self.update_raw_shipment(raw_id, address.id)
            return True
        else:
            self.mark_failed(raw_id)
            return False

    def test_connection(self) -> bool:
        return self.database.test_connection()

    def _save_validated_address(self, raw_id: int, address: Address) -> None:
        conn = self.database.get_connection()
        logger.info("Saving address to customers_validated: %s", address)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO customers_validated
                    (address_one, address_two, city, state, zip, longitude,
                     latitude, timezone, raw, updated_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    (address.address_one, address.address_two, address.city,
                     address.state, address.zip, address.longitude,
                     address.latitude, address.timezone, address.residential),
                )
                address.id = cur.lastrowid
                logger.info(f"{address.id} saved")
                if address.id is not None:
                    self.update_raw_shipment(raw_id, address.id)
        except pymysql.err.Error as e:
            logger.error("save_validated_address failed: %s", e)

    @staticmethod
    def _map_rows_to_shipments(rows) -> List[Shipment]:
        shipments = []

        for row in rows:
            address = Address(
                address_one=row.get("recip_address"),
                address_two=row.get("recip_address_2"),
                city=row.get("recip_city"),
                state=row.get("recip_state"),
                zip=row.get("recip_zip"),
                id=row.get("validated_id"),
                valid=False
            )
            shipment = Shipment(
                raw_id=row.get("id"),
                address=address,
            )

            shipments.append(shipment)

        return shipments
