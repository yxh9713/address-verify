import threading

from requests.exceptions import RequestException
from smartystreets_python_sdk import BasicAuthCredentials, ClientBuilder, exceptions
from smartystreets_python_sdk.us_street import Lookup
from smartystreets_python_sdk.us_street.match_type import MatchType

from adapters.address_validator import AddressValidator
from entities.address import Address
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SmartyAddress(AddressValidator):
    def __init__(self, auth_id: str, auth_token: str):
        credentials = BasicAuthCredentials(auth_id, auth_token)
        self.client = ClientBuilder(credentials).build_us_street_api_client()
        # main.py shares this adapter across workers; mirror Java's synchronized send.
        self._lock = threading.Lock()

    def validate(self, address: Address) -> Address:
        lookup = Lookup()
        lookup.street = address.address_one
        lookup.city = address.city
        lookup.state = address.state
        lookup.zipcode = address.zip
        # The Java implementation uses the API's default strict matching rule.
        lookup.match = MatchType.STRICT

        try:
            with self._lock:
                self.client.send_lookup(lookup)
        except (exceptions.SmartyException, RequestException, OSError) as error:
            # Transport exceptions may contain credential-bearing request URLs.
            logger.error("Smarty validation failed (%s)", type(error).__name__)
            return address

        if not lookup.result:
            return address

        candidate = lookup.result[0]
        components = candidate.components
        metadata = candidate.metadata

        # Preserve the Java reference's component order and default-city preference.
        return Address(
            address_one=" ".join(part for part in (
                components.primary_number,
                components.street_predirection,
                components.street_name,
                components.street_postdirection,
                components.street_suffix,
            ) if part),
            address_two=" ".join(part for part in (
                components.secondary_designator,
                components.secondary_number,
            ) if part),
            city=components.default_city_name or components.city_name,
            state=components.state_abbreviation,
            zip=(components.zipcode or "")[:5],
            latitude=metadata.latitude if metadata else None,
            longitude=metadata.longitude if metadata else None,
            timezone=metadata.time_zone if metadata else None,
            residential={
                "Residential": "RESIDENCE",
                "Commercial": "BUSINESS",
            }.get(metadata.rdi) if metadata else None,
            valid=True,
        )
