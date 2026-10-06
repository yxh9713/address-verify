from adapters.address_validator import AddressValidator
from core.config import Config


def create_validator(config: Config) -> AddressValidator:
    if config.processor == "ep":
        from adapters.ep_address import EpAddress

        return EpAddress(config.easypost_api_key)
    if config.processor == "smarty":
        from adapters.smarty_address import SmartyAddress

        return SmartyAddress(config.smarty_auth_id, config.smarty_auth_token)
    raise ValueError(f"Unsupported PROCESSOR {config.processor!r}; expected 'ep' or 'smarty'")
