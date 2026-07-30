import logging
import json
import redis
import hashlib

from entities.shipment import Address

CACHE_TTL_SECONDS = 60 * 60 * 24 * 30 # 30 days

logger = logging.getLogger(__name__)

class RedisCache:

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    def set(self, address):
        key = self._address_to_hash(address)
        ss = self._serialize(address)
        logger.info(f"redis setting {key}")
        logger.info(f"ss: {ss}")
        self.redis_client.set(key, self._serialize(address))

    def get(self, address: Address):
        key = self._address_to_hash(address)
        try:
            raw = self.redis_client.get(key)
        except redis.RedisError as e:
            logger.error(f"redis error: {e}")
            raw = None

        if raw is not None:
            return self._deserialize(raw)

        return None

    @staticmethod
    def _serialize(address: Address) -> str:
        return json.dumps({
            "address_one": address.address_one,
            "address_two": address.address_two,
            "city": address.city,
            "state": address.state,
            "zip": address.zip,
            "longitude": address.longitude,
            "latitude": address.latitude,
            "timezone": address.timezone,
            "residential": address.residential,
            "valid": address.valid,
            "id": address.id
        })

    @staticmethod
    def _deserialize(data):
        value = json.loads(data)
        return Address(**value)

    @staticmethod
    def _address_to_hash(address: Address):
        address_string = (address.address_one + address.city + address.state + address.zip).encode("utf-8")
        hashed = hashlib.sha256(address_string)
        return "ADDRESS:" + hashed.hexdigest()
