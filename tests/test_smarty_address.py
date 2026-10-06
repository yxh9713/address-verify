import unittest
from unittest.mock import Mock, patch

from requests.exceptions import ConnectionError, Timeout
from smartystreets_python_sdk import exceptions
from smartystreets_python_sdk.us_street import Candidate
from smartystreets_python_sdk.us_street.match_type import MatchType

from adapters.smarty_address import SmartyAddress
from entities.address import Address


def candidate(**overrides):
    data = {
        "components": {
            "primary_number": "123", "street_predirection": "N",
            "street_name": "Main", "street_postdirection": "W", "street_suffix": "St",
            "secondary_designator": "Apt", "secondary_number": "2",
            "default_city_name": "Salt Lake City", "city_name": "SLC",
            "state_abbreviation": "UT", "zipcode": "84101", "plus4_code": "1234",
        },
        "metadata": {
            "latitude": 40.76, "longitude": -111.89,
            "time_zone": "Mountain", "rdi": "Residential",
        },
    }
    data.update(overrides)
    return Candidate(data)


class SmartyAddressTests(unittest.TestCase):
    def setUp(self):
        self.validator = SmartyAddress("test-id", "test-token")
        self.validator.client = Mock()
        self.address = Address(address_one="123 main", city="SLC", state="UT", zip="84101")

    def respond(self, *results):
        def send(lookup):
            lookup.result = list(results)
        self.validator.client.send_lookup.side_effect = send

    def test_request_and_response_match_java_reference(self):
        self.respond(candidate(), candidate(components={"primary_number": "999"}))
        result = self.validator.validate(self.address)
        lookup = self.validator.client.send_lookup.call_args.args[0]
        self.assertEqual(
            (lookup.street, lookup.city, lookup.state, lookup.zipcode),
            (self.address.address_one, self.address.city, self.address.state, self.address.zip),
        )
        self.assertEqual(lookup.match, MatchType.STRICT)
        self.assertEqual(result, Address(
            address_one="123 N Main W St", address_two="Apt 2", city="Salt Lake City",
            state="UT", zip="84101", latitude=40.76, longitude=-111.89,
            timezone="Mountain", residential="RESIDENCE", valid=True,
        ))
        self.assertFalse(self.address.valid)
        self.assertIsNone(result.id)

    def test_optional_components_and_metadata_can_be_absent(self):
        self.respond(candidate(components={
            "primary_number": "123", "street_name": "Main", "city_name": "SLC",
            "state_abbreviation": "UT", "zipcode": "84101",
        }, metadata={}))
        result = self.validator.validate(self.address)
        self.assertTrue(result.valid)
        self.assertEqual(result.address_one, "123 Main")
        self.assertEqual(result.address_two, "")
        self.assertEqual(result.city, "SLC")
        for name in ("latitude", "longitude", "timezone", "residential"):
            self.assertIsNone(getattr(result, name))

    def test_residential_mapping_and_partial_metadata(self):
        for rdi, expected in (("Commercial", "BUSINESS"), ("Residential", "RESIDENCE"),
                              ("Unknown", None), (None, None)):
            with self.subTest(rdi=rdi):
                self.respond(candidate(metadata={"rdi": rdi, "latitude": 0.0}))
                result = self.validator.validate(self.address)
                self.assertEqual(result.residential, expected)
                self.assertEqual(result.latitude, 0.0)
                self.assertIsNone(result.longitude)
                self.assertTrue(result.valid)

    def test_no_candidates_returns_original_unvalidated_address(self):
        self.assertIs(self.validator.validate(self.address), self.address)
        self.assertFalse(self.address.valid)

    def test_api_and_transport_errors_return_original_without_logging_secrets(self):
        for error_type in (exceptions.BadCredentialsError, exceptions.TooManyRequestsError,
                           Timeout, ConnectionError, OSError):
            with self.subTest(error=error_type.__name__):
                self.validator.client.send_lookup.side_effect = error_type("secret-token-in-url")
                with self.assertLogs("adapters.smarty_address", level="ERROR") as logs:
                    self.assertIs(self.validator.validate(self.address), self.address)
                self.assertFalse(self.address.valid)
                self.assertNotIn("secret-token-in-url", " ".join(logs.output))

    def test_shared_adapter_serializes_sdk_calls(self):
        # Sending happens under the same lock as Java's synchronized validate method.
        def send(lookup):
            self.assertTrue(self.validator._lock.locked())
        self.validator.client.send_lookup.side_effect = send
        self.validator.validate(self.address)
        self.assertFalse(self.validator._lock.locked())


if __name__ == "__main__":
    unittest.main()
