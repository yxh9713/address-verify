import threading
import logging

from adapters.address_validator import AddressValidator
from adapters.mysql_cache import MySQLCache
from adapters.redis_cache import RedisCache
from adapters.shipment_gateway import ShipmentGateway

logger = logging.getLogger(__name__)

class ShipmentAddressProcessor:
    def __init__(
        self,
        worker_id: int,
        gateway: ShipmentGateway,
        redis_cache: RedisCache,
        mysql_cache: MySQLCache,
        validator: AddressValidator,
        sleep_timeout_ms: int,
    ):
        self.worker_id = worker_id
        self.gateway = gateway
        self.redis_cache = redis_cache
        self.mysql_cache = mysql_cache
        self.validator = validator
        self.sleep_seconds = sleep_timeout_ms / 1000.0
        self._last_run_idle = True

    def run_forever(self, stop_event: threading.Event):
        while not stop_event.is_set():
            try:
                self._run_once()
            except Exception:
                logger.exception("Worker %s: unhandled error in processing loop", self.worker_id)
            stop_event.wait(self.sleep_seconds if self._last_run_idle else 0.01)

    def _run_once(self):
        if not self.gateway.test_connection():
            self._last_run_idle = True
            return

        shipments = self.gateway.get_shipments(self.worker_id)

        if not shipments:
            logger.info(f"No shipments for worker {self.worker_id}")
            self._last_run_idle = True
            return

        self._last_run_idle = False
        for shipment in shipments:
            raw_id = shipment.raw_id
            address = shipment.address

            if not address.check_required_fields():
                self.gateway.mark_failed(raw_id)
                continue

            # check redis cache
            cached = self.redis_cache.get(address)
            logger.info(f"find redis cache {cached}")

            # check mysql cache
            if cached is None:
                cached = self.mysql_cache.get(address)
                logger.info(f"find mysql cache {cached}")

            if cached is not None and cached.id is not None:
                self.gateway.update_raw_shipment(raw_id, cached.id)
            else:
                logger.info(f"EP validate address {address}")
                validated = self.validator.validate(address)
                if self.gateway.save_address(raw_id, validated):
                    self.redis_cache.set(validated)

            return
