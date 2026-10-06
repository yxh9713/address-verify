# Address validation worker

A Python worker that reads pending US shipment addresses from MySQL, checks Redis
and MySQL for cached results, and validates uncached addresses with 3rd party apis.

## Run

Use Python 3.10 or newer. This repository does not include schema migrations.
Redis must also be available; the worker uses Redis database 1.

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp env_sample .env
```

Edit `.env` with your database, Redis, and provider credentials, then start the
worker from the project directory:

```sh
python3 main.py
```

Stop with Ctrl+C or SIGTERM. Logs are written to `logs/worker.log` and the console.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests use SDK response objects and mocked clients, gateways, and caches. They do
not require credentials or contact Smarty, EasyPost, MySQL, or Redis.
