import json

import easypost
from easypost.errors import ApiError

from adapters.address_validator import AddressValidator
from entities.address import Address
from utils.logger import setup_logger

logger = setup_logger(__name__)

class EpAddress(AddressValidator):
    def __init__(self, easypost_api_key:str):
        self.client = easypost.EasyPostClient(easypost_api_key)

    def validate(self, address: Address):
        try:
            params = {
                "street1": address.address_one,
                "city": address.city,
                "state": address.state,
                "zip": address.zip,
                "country": "US"
            }

            verified = self.client.address.create_and_verify(**params)

            valid_address = Address()
            valid_address.address_one = verified.street1
            valid_address.address_two = verified.street2
            valid_address.city = verified.city
            valid_address.state = verified.state
            valid_address.zip = (verified.zip or "")[:5]
            valid_address.residential = "RESIDENCE" if verified.residential == "true" else "BUSINESS"
            valid_address.valid = True

            delivery = verified.verifications.get("delivery")
            details = delivery.details if delivery else None
            latitude = getattr(details, "latitude", None) if details else None
            longitude = getattr(details, "longitude", None) if details else None
            time_zone = getattr(details, "time_zone", None) if details else None

            if latitude is None or longitude is None or time_zone is None:
                return valid_address

            valid_address.latitude = latitude
            valid_address.longitude = longitude
            valid_address.timezone = time_zone

            return valid_address

        except ApiError as e:
            # This will print the exact reason EasyPost rejected it
            print("--- EasyPost API Error ---")
            print(f"Message: {e.message}")
            print(f"HTTP Status: {e.http_status}")

            # EasyPost provides a list of specific field errors
            if hasattr(e, 'errors') and e.errors:
                print("Detailed Errors:")
                for err in e.errors:
                    logger.error(f" EasyPost API Error: {err}")
            print("--------------------------\n")

            # return the unvalidated address on failure
            return address
