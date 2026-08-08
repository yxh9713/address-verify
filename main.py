
from concurrent.futures.thread import ThreadPoolExecutor

import redis
import threading
import signal # intercept messages sent directly by the OS

from adapters import ep_address
from adapters.mysql_cache import MySQLCache
from adapters.redis_cache import RedisCache
from adapters.shipment_gateway import ShipmentGateway
from core.config import load_config
from core.db import Database
from core.worker import ShipmentAddressProcessor
from utils.logger import setup_logger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s %(name)s - %(message)s",
)
logger = setup_logger(__name__)

def main():
    config = load_config()

    # shared clients
    redis_client = redis.Redis(
        host = config.redis_host,
        port = config.redis_port,
        decode_responses = True,
        db=1,
        protocol=2,
    )
    redis_cache = RedisCache(redis_client)
    validator = ep_address.EpAddress(config.easypost_api_key)

    stop_event = threading.Event()

    def handle_shoutdown(signum, frame):
        logger.info(f"Shoutdown worker {signum}, {frame}")
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_shoutdown)
    signal.signal(signal.SIGINT, handle_shoutdown)

    with ThreadPoolExecutor(max_workers=config.core_pool_size, thread_name_prefix="worker") as executor:
        futures = []
        for worker_id in range(config.core_pool_size):
            # Each worker gets its own MySQL connection/cache stack
            database = Database(config)
            mysql_cache = MySQLCache(database)
            gateway = ShipmentGateway(database)
            processor = ShipmentAddressProcessor(
                worker_id=worker_id,
                gateway=gateway,
                redis_cache=redis_cache,
                mysql_cache=mysql_cache,
                validator=validator,
                sleep_timeout_ms=config.timeout_ms,
            )
            futures.append(executor.submit(processor.run_forever, stop_event))

        for future in futures:
            future.result()


    # TEST 1 WORKER
    # worker_id = 1
    # database = Database(config)
    # redis_client = redis.Redis(
    #     host = config.redis_host,
    #     port = config.redis_port,
    #     decode_responses = True,
    #     db=1,
    #     protocol=2,
    # )
    # redis_cache = RedisCache(redis_client)
    # mysql_cache = MySQLCache(database)
    # gateway = ShipmentGateway(database)
    # validator = ep_address.EpAddress(config.easypost_api_key)
    # processor = ShipmentAddressProcessor(
    #     worker_id=worker_id,
    #     gateway=gateway,
    #     redis_cache=redis_cache,
    #     mysql_cache=mysql_cache,
    #     validator=validator,
    #     sleep_timeout_ms=config.timeout_ms,
    # )
    #
    # processor._run_once()

if __name__ == "__main__":
    main()
