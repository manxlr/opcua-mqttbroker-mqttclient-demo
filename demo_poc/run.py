"""
OPC → MQTT demo: embedded aMQTT broker, OPC bridge, Flask (dashboard + admin).

From project root:
  .\\venv\\Scripts\\python demo_poc\\run.py

Then open http://127.0.0.1:5050/  (dashboard) and http://127.0.0.1:5050/admin
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo_poc.app import create_app, ensure_config_file
from demo_poc.broker_runner import EmbeddedBroker
from demo_poc.opc_bridge import OpcMqttBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# High-frequency OPC reads otherwise spam asyncua INFO lines per read.
for _name in ("asyncua", "amqtt", "transitions", "websockets"):
    logging.getLogger(_name).setLevel(logging.WARNING)
log = logging.getLogger("demo_poc")


def main() -> None:
    base = Path(__file__).resolve().parent
    config_path = base / "config.json"
    default_path = base / "config.default.json"
    broker_yaml = base / "broker_config.yaml"

    ensure_config_file(config_path, default_path)

    broker = EmbeddedBroker(broker_yaml)
    log.info("Starting embedded MQTT broker (TCP + WebSocket)…")
    broker.start(wait_seconds=3.0)

    bridge = OpcMqttBridge(config_path)
    bridge.start()

    app = create_app(config_path=config_path, bridge=bridge)
    try:
        log.info("Flask http://127.0.0.1:5050/  (dashboard)  http://127.0.0.1:5050/admin")
        app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=False, threaded=True)
    finally:
        log.info("Stopping…")
        bridge.stop()
        broker.stop()


if __name__ == "__main__":
    main()
