"""OPC UA polling bridge: read enabled nodes and publish JSON to MQTT."""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from asyncua import ua
from asyncua.sync import Client

logger = logging.getLogger(__name__)

# Sensible default parent to browse CODESYS global vars (edit device name if needed).
DEFAULT_BROWSE_PARENT = (
    "ns=4;s=|var|CODESYS Control Win V3 x64.Application.GVL_AxisData"
)


def opc_browse_children(opc_url: str, parent_node_id: str) -> dict[str, Any]:
    """List direct children under an OPC UA node (for admin UI — pick variables to publish)."""
    client = Client(opc_url)
    try:
        client.connect()
        parent = client.get_node(parent_node_id)
        children = parent.get_children()
        rows: list[dict[str, Any]] = []
        for ch in children:
            try:
                bn = ch.read_browse_name()
                nid = ch.nodeid.to_string()
                nc = ch.read_node_class()
                nc_name = nc.name
                rows.append(
                    {
                        "browse_name": bn.Name,
                        "node_id": nid,
                        "node_class": nc_name,
                        "is_variable": nc == ua.NodeClass.Variable,
                    }
                )
            except Exception as ex:
                rows.append({"error": str(ex)})
        return {"ok": True, "children": rows}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def opc_test_read(opc_url: str, node_id: str) -> dict[str, Any]:
    """One-shot read for admin 'Test OPC' button."""
    client = Client(opc_url)
    try:
        client.connect()
        node = client.get_node(node_id)
        val = node.read_value()
        return {"ok": True, "value": _json_safe(val)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def _json_safe(value: Any) -> Any:
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, str):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


class OpcMqttBridge:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._last_error: str | None = None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def load_config(self) -> dict[str, Any]:
        with self._config_path.open(encoding="utf-8") as f:
            return json.load(f)

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="opc-mqtt-bridge", daemon=True)
        self._thread.start()

    def stop(self, join_timeout: float = 8.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=join_timeout)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                cfg = self.load_config()
                self._loop_session(cfg)
            except Exception as e:
                with self._lock:
                    self._last_error = str(e)
                logger.warning("bridge session error: %s", e)
                if self._stop.wait(timeout=2.0):
                    break

    def _loop_session(self, cfg: dict[str, Any]) -> None:
        opc_url = cfg["opc_url"]
        poll_ms = max(10, int(cfg.get("poll_interval_ms", 100)))
        prefix = cfg.get("topic_prefix", "opc").strip("/") or "opc"
        host = cfg.get("mqtt_host", "127.0.0.1")
        port = int(cfg.get("mqtt_port", 1883))

        signals = [s for s in cfg.get("signals", []) if s.get("enabled", True)]
        if not signals:
            with self._lock:
                self._last_error = "No enabled signals"
            while not self._stop.wait(timeout=0.5):
                pass
            return

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="opc_bridge_demo",
        )

        try:
            client.connect(host, port, keepalive=60)
            client.loop_start()
        except Exception as e:
            with self._lock:
                self._last_error = f"MQTT connect failed: {e}"
            raise

        ua = Client(opc_url)
        try:
            ua.connect()
            nodes = [ua.get_node(s["node_id"]) for s in signals]
            with self._lock:
                self._last_error = None

            while not self._stop.is_set():
                try:
                    values = ua.read_values(nodes)
                    ts = int(time.time() * 1000)
                    for sig, val in zip(signals, values, strict=True):
                        sid = sig["id"]
                        topic = f"{prefix}/{sid}"
                        payload = {
                            "ts": ts,
                            "id": sid,
                            "node_id": sig["node_id"],
                            "value": _json_safe(val),
                        }
                        raw = json.dumps(payload, separators=(",", ":"))
                        client.publish(topic, raw.encode("utf-8"), qos=0)
                except Exception as e:
                    with self._lock:
                        self._last_error = str(e)
                    logger.warning("read/publish failed: %s", e)
                    break

                if self._stop.wait(timeout=poll_ms / 1000.0):
                    break
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                logger.exception("mqtt cleanup")
            try:
                ua.disconnect()
            except Exception:
                logger.exception("opc disconnect")
