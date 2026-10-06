import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # MySQL
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_db: str

    # Redis
    redis_host: str
    redis_port: int

    # EasyPost
    easypost_api_key: str

    # Threading / job behavior
    core_pool_size: int
    timeout_ms: int
    look_back_days: int

    # Address validation provider (EasyPost remains the default)
    processor: str = "ep"
    smarty_auth_id: str = ""
    smarty_auth_token: str = ""

def _get_int(name: str, default: int):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value.strip())

def load_config() -> Config:
    processor = os.getenv("PROCESSOR", "ep").strip().lower()
    if processor not in ("ep", "smarty"):
        raise ValueError(f"Unsupported PROCESSOR {processor!r}; expected 'ep' or 'smarty'")

    required_credentials = (
        ("EASYPOST_API_KEY",) if processor == "ep"
        else ("SMARTY_AUTH_ID", "SMARTY_AUTH_TOKEN")
    )
    for name in required_credentials:
        if not os.getenv(name, "").strip():
            raise ValueError(f"{name} is required when PROCESSOR={processor}")

    return Config(
        mysql_host=os.environ["DB_HOST"],
        mysql_port=_get_int("DB_PORT", 3306),
        mysql_user=os.environ["DB_USER"],
        mysql_password=os.environ["DB_PASSWORD"],
        mysql_db=os.environ["DB_NAME"],

        redis_host=os.environ["REDIS_HOST"],
        redis_port=_get_int("REDIS_PORT", 6379),
        easypost_api_key=os.getenv("EASYPOST_API_KEY", "").strip(),
        core_pool_size=int(_get_int("CORE_POOL_SIZE", 3)),
        timeout_ms=int(_get_int("TIMEOUT_MS", 5000)),
        look_back_days=int(_get_int("LOOK_BACK", 4)),
        processor=processor,
        smarty_auth_id=os.getenv("SMARTY_AUTH_ID", "").strip(),
        smarty_auth_token=os.getenv("SMARTY_AUTH_TOKEN", "").strip(),
    )
