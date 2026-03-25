"""Run embedded aMQTT broker in a background thread with its own asyncio loop."""

from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any

import yaml
from amqtt.broker import Broker
from amqtt.contexts import BrokerConfig

logger = logging.getLogger(__name__)


def load_broker_config_dict(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        msg = f"Broker config must be a mapping: {path}"
        raise ValueError(msg)
    return data


class EmbeddedBroker:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._started = threading.Event()

    def start(self, wait_seconds: float = 1.0) -> None:
        """Start broker on a daemon thread (non-blocking)."""
        self._stop.clear()
        self._started.clear()
        self._thread = threading.Thread(target=self._run, name="amqtt-broker", daemon=True)
        self._thread.start()
        if not self._started.wait(timeout=wait_seconds):
            logger.warning("Embedded broker did not signal start within %.1fs", wait_seconds)

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        cfg_dict = load_broker_config_dict(self._config_path)
        bc = BrokerConfig.from_dict(cfg_dict)
        broker = Broker(bc, loop=loop)

        async def main() -> None:
            await broker.start()
            self._started.set()
            while not self._stop.is_set():
                await asyncio.sleep(0.2)
            await broker.shutdown()

        try:
            loop.run_until_complete(main())
        except Exception:
            logger.exception("broker thread failed")
            self._started.set()
        finally:
            loop.close()

    def stop(self, join_timeout: float = 8.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=join_timeout)
