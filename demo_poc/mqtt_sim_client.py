"""
Second MQTT client (simulator) — subscribes to the same broker and prints messages.

This does NOT talk to OPC. It only connects to the embedded broker (TCP 1883) like any
MQTT subscriber (e.g. another PLC, Node-RED, or a second PC).

From project root, with demo running:

    .\\venv\\Scripts\\python demo_poc\\mqtt_sim_client.py

Optional:

    .\\venv\\Scripts\\python demo_poc\\mqtt_sim_client.py --topic "opc/#"
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time

import paho.mqtt.client as mqtt


def main() -> int:
    p = argparse.ArgumentParser(description="Subscribe to MQTT and print JSON payloads (POC simulator).")
    p.add_argument("--host", default="127.0.0.1", help="Broker host (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=1883, help="Broker TCP port (default 1883)")
    p.add_argument("--topic", default="opc/#", help="Topic filter (default opc/#)")
    args = p.parse_args()

    stop = False

    def on_signal(*_: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    def on_connect(client: mqtt.Client, _userdata: object, _flags: dict, reason_code: mqtt.ReasonCode, _props: object) -> None:
        if reason_code.is_failure:
            print(f"Connect failed: {reason_code}", file=sys.stderr)
            return
        print(f"Connected to mqtt://{args.host}:{args.port}, subscribing {args.topic!r}")
        client.subscribe(args.topic, qos=0)

    def on_message(_client: mqtt.Client, _userdata: object, msg: mqtt.MQTTMessage) -> None:
        t = time.strftime("%H:%M:%S")
        try:
            j = json.loads(msg.payload.decode("utf-8"))
            pretty = json.dumps(j, separators=(",", ":"))
        except Exception:
            pretty = msg.payload.decode("utf-8", errors="replace")
        print(f"[{t}] {msg.topic}  {pretty}")

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"mqtt_sim_{int(time.time()) % 100000}",
    )
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(args.host, args.port, keepalive=60)
    except Exception as e:
        print(f"Cannot connect: {e}", file=sys.stderr)
        return 1

    client.loop_start()
    try:
        while not stop:
            time.sleep(0.25)
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
