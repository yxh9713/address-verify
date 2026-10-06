import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from smartystreets_python_sdk.us_street import Candidate

from adapters.ep_address import EpAddress
from adapters.redis_cache import RedisCache
from adapters.shipment_gateway import ShipmentGateway
from adapters.smarty_address import SmartyAddress
from core.worker import ShipmentAddressProcessor
from entities.address import Address
from entities.shipment import Shipment


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.gateway = ShipmentGateway(Mock())
        self.gateway.test_connection = Mock(return_value=True)
        self.gateway.get_shipments = Mock()
        self.gateway.mark_failed = Mock()
        self.gateway.update_raw_shipment = Mock()
        self.gateway._save_validated_address = Mock(side_effect=self.save)
        self.redis_cache = RedisCache(Mock())
        self.redis_cache.redis_client.get.return_value = None
        self.mysql_cache = Mock()
        self.mysql_cache.get.return_value = None
        self.validator = Mock()
        self.address = Address(address_one="123 Main St", city="SLC", state="UT", zip="84101")
        self.gateway.get_shipments.return_value = [Shipment(42, self.address)]

    def save(self, raw_id, address):
        address.id = 99
        self.gateway.update_raw_shipment(raw_id, address.id)

    def run_once(self, validator=None):
        worker = ShipmentAddressProcessor(
            0, self.gateway, self.redis_cache, self.mysql_cache,
            validator if validator is not None else self.validator, 5000,
        )
        worker._run_once()
        return worker

    def test_incomplete_input_is_failed_and_next_record_is_processed(self):
        cached = Address(id=99, valid=True)
        self.redis_cache.redis_client.get.return_value = RedisCache._serialize(cached)
        self.gateway.get_shipments.return_value = [
            Shipment(41, Address(address_one="123 Main", city="SLC", state="UT")),
            Shipment(42, self.address),
        ]
        self.run_once()
        self.gateway.mark_failed.assert_called_once_with(41)
        self.gateway.update_raw_shipment.assert_called_once_with(42, 99)
        self.validator.validate.assert_not_called()

    def test_redis_hit_skips_mysql_and_api(self):
        self.redis_cache.redis_client.get.return_value = RedisCache._serialize(Address(id=99))
        self.run_once()
        self.gateway.update_raw_shipment.assert_called_once_with(42, 99)
        self.mysql_cache.get.assert_not_called()
        self.validator.validate.assert_not_called()

    def test_mysql_hit_skips_api(self):
        self.mysql_cache.get.return_value = Address(id=99)
        self.run_once()
        self.mysql_cache.get.assert_called_once_with(self.address)
        self.gateway.update_raw_shipment.assert_called_once_with(42, 99)
        self.validator.validate.assert_not_called()

    def test_both_providers_save_and_cache_same_address_model(self):
        for name in ("ep", "smarty"):
            with self.subTest(provider=name):
                self.setUp()
                if name == "ep":
                    validator = EpAddress("test-key")
                    validator.client = Mock()
                    validator.client.address.create_and_verify.return_value = SimpleNamespace(
                        street1="123 Main St", street2="", city="SLC", state="UT",
                        zip="84101-1234", residential="true", verifications={},
                    )
                else:
                    validator = SmartyAddress("test-id", "test-token")
                    validator.client = Mock()
                    def respond(lookup):
                        lookup.result = [Candidate({"components": {
                            "primary_number": "123", "street_name": "Main", "street_suffix": "St",
                            "city_name": "SLC", "state_abbreviation": "UT", "zipcode": "84101",
                        }})]
                    validator.client.send_lookup.side_effect = respond
                self.run_once(validator)
                self.gateway._save_validated_address.assert_called_once()
                self.gateway.update_raw_shipment.assert_called_once_with(42, 99)
                self.gateway.mark_failed.assert_not_called()
                call = self.redis_cache.redis_client.set.call_args
                cached = RedisCache._deserialize(call.args[1])
                self.assertTrue(cached.valid)
                self.assertEqual(cached.id, 99)
                self.assertEqual(cached.zip, "84101")
                self.assertEqual(cached.address_one, "123 Main St")
                self.assertEqual(call.kwargs["ex"], 90 * 24 * 60 * 60)

    def test_smarty_no_match_marks_failed_and_does_not_cache(self):
        validator = SmartyAddress("test-id", "test-token")
        validator.client = Mock()
        self.run_once(validator)
        self.gateway.mark_failed.assert_called_once_with(42)
        self.gateway._save_validated_address.assert_not_called()
        self.redis_cache.redis_client.set.assert_not_called()

    def test_idle_poll_delay_is_preserved(self):
        self.gateway.get_shipments.return_value = []
        worker = self.run_once()
        self.assertTrue(worker._last_run_idle)
        self.assertEqual(worker.sleep_seconds, 5.0)


if __name__ == "__main__":
    unittest.main()
