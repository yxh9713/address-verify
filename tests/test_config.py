import os
import unittest
from unittest.mock import patch

from adapters.ep_address import EpAddress
from adapters.smarty_address import SmartyAddress
from adapters.validator_factory import create_validator
from core.config import load_config


BASE_ENV = {
    "DB_HOST": "localhost", "DB_USER": "test", "DB_PASSWORD": "test",
    "DB_NAME": "test", "REDIS_HOST": "localhost",
}


class ConfigTests(unittest.TestCase):
    def load(self, **values):
        with patch.dict(os.environ, {**BASE_ENV, **values}, clear=True):
            return load_config()

    def test_default_selects_easypost_without_smarty_credentials(self):
        config = self.load(EASYPOST_API_KEY="test-ep-key")
        self.assertEqual(config.processor, "ep")
        self.assertIsInstance(create_validator(config), EpAddress)

    def test_explicit_ep_selects_easypost(self):
        config = self.load(PROCESSOR="ep", EASYPOST_API_KEY="test-ep-key")
        self.assertIsInstance(create_validator(config), EpAddress)

    def test_smarty_does_not_require_easypost_credentials(self):
        config = self.load(
            PROCESSOR="smarty", SMARTY_AUTH_ID="test-id", SMARTY_AUTH_TOKEN="test-token",
        )
        self.assertEqual(config.easypost_api_key, "")
        self.assertIsInstance(create_validator(config), SmartyAddress)

    def test_processor_is_case_insensitive_and_trims_whitespace(self):
        config = self.load(
            PROCESSOR=" SMARTY ", SMARTY_AUTH_ID="test-id", SMARTY_AUTH_TOKEN="test-token",
        )
        self.assertEqual(config.processor, "smarty")

    def test_unsupported_and_empty_processor_fail_before_connections(self):
        for value in ("invalid", ""):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Unsupported PROCESSOR"):
                self.load(PROCESSOR=value)

    def test_factory_rejects_unsupported_processor(self):
        config = self.load(EASYPOST_API_KEY="test-ep-key")
        config.processor = "invalid"
        with self.assertRaisesRegex(ValueError, "Unsupported PROCESSOR"):
            create_validator(config)

    def test_missing_or_blank_selected_credentials_fail_clearly(self):
        for name in ("EASYPOST_API_KEY", "SMARTY_AUTH_ID", "SMARTY_AUTH_TOKEN"):
            for value in (None, "   "):
                env = {
                    "PROCESSOR": "ep" if name == "EASYPOST_API_KEY" else "smarty",
                    "EASYPOST_API_KEY": "test-key", "SMARTY_AUTH_ID": "test-id",
                    "SMARTY_AUTH_TOKEN": "test-token",
                }
                if value is None:
                    env.pop(name)
                else:
                    env[name] = value
                with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, name):
                    self.load(**env)


if __name__ == "__main__":
    unittest.main()
