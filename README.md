# CODESYS OPC UA -> MQTT -> Real-time Dashboard (Community POC)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#)
[![OPC UA](https://img.shields.io/badge/OPC%20UA-Client%2FServer-brightgreen)](#)
[![MQTT](https://img.shields.io/badge/MQTT-PubSub-brightgreen)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## Overview

This repository demonstrates an end-to-end proof-of-concept data pipeline:

1. **CODESYS PLC** exposes variables via **OPC UA**
2. **Python bridge** reads those OPC UA nodes and publishes JSON messages to **MQTT** topics
3. An embedded **MQTT broker (aMQTT)** serves MQTT to multiple clients
4. A **Flask** web UI (glass/neon) subscribes over **MQTT over WebSocket** and plots live charts
5. Optional **MQTT clients** (terminal simulator + desktop GUI) also subscribe and plot/export

Screenshots are optional placeholders; add your own images under `Screenshots/`.

## Screenshots

Place images here:
- `Screenshots/screenshot-dashboard.png`
- `Screenshots/screenshot-admin-browse.png`
- `Screenshots/screenshot-terminal-simulator.png`
- `Screenshots/screenshot-desktop-gui.png`

Then update links in this README.

## Architecture (high level)

```mermaid
flowchart LR
  subgraph plc[CODESYS]
    opc[OPC UA Server :4840]
  end

  subgraph python[Python demo (bridge + UI)]
    bridge[OPC UA client (asyncua.sync) + MQTT publisher]
    flask[Flask web app (dashboard + admin)]
    broker[aMQTT broker (TCP 1883 + WS 9001)]
  end

  subgraph clients[MQTT Clients]
    web[Browser dashboard (mqtt.js)]
    term[Terminal simulator]
    gui[Desktop GUI plots]
    opc_examples[Original Python OPC examples]
  end

  opc -->|read values / browse| bridge
  bridge -->|publish JSON to topics: opc/<signal>| broker
  broker -->|MQTT over WebSocket| web
  broker -->|MQTT TCP| term
  broker -->|MQTT TCP| gui

  opc_examples -->|optional: test OPC directly| opc
```

## Default endpoints / topic format

- OPC UA server (default, used by the Python bridge): `opc.tcp://localhost:4840`
- MQTT broker ports (embedded):
  - MQTT TCP: `127.0.0.1:1883`
  - MQTT WebSocket (for browser): `127.0.0.1:9001`
- MQTT topic convention used by the bridge:
  - `opc/<signal_id>`
- JSON payload (example):
  - `{"ts": 1710000000000, "id": "lrAxisPosition", "node_id": "ns=4;s=...", "value": 12.34}`

## Requirements

- Windows recommended (this project runs on your machine).
- CODESYS OPC UA server running (simulation or real PLC).
- Python venv (recommended).

## Quick start

From this repository root:

1. Create venv + install dependencies

```bash
python -m venv .venv
.
.venv\Scripts\activate
pip install -r requirements-demo.txt
```

2. Start the demo (starts embedded broker + bridge + Flask)

```bash
python demo_poc\run.py
```

3. Open the UI

- Dashboard: `http://127.0.0.1:5050/`
- Bridge admin: `http://127.0.0.1:5050/admin`

On the dashboard:
- WebSocket URL: `ws://127.0.0.1:9001`
- Subscribe pattern: `opc/#`

On the admin page:
- Click `Fetch variables from OPC (browse)` to populate the list of OPC nodes from your CODESYS global folder.
- Click `Save & restart bridge`.

## MQTT client options

With the demo running:

### Terminal MQTT simulator

```bash
.
.venv\Scripts\python demo_poc\mqtt_sim_client.py
```

### Desktop GUI (plots + export)

```bash
.
.venv\Scripts\python demo_poc\mqtt_gui_client.py
```

It connects to MQTT TCP `127.0.0.1:1883` and subscribes to `opc/#` by default.

## Original OPC UA Python examples

Folder: `Python_Script/`

These scripts demonstrate direct OPC UA reading with `asyncua.sync`:
- `connect_to_server.py`
- `plot_data_from_server.py`
- `plot_multiple_data_from_server.py`

## Included CoDeSys project export

Folder: `CoDeSys/`

This repository includes an exported CODESYS project bundle for the OPC UA server example.
In CODESYS:
- Open the file `CoDeSys/OPC-UA_Server Example Project - Start.project`
- Build the project
- Start PLC simulation or run on real PLC
- Ensure OPC UA variables are exposed (anonymous allowed, SecurityPolicy None) like in your original setup

The bridge admin supports browsing variables so you do not have to hardcode NodeIds.

## Acknowledgements

- CODESYS OPC UA server example project (exported from your CoDeSys workspace)
- aMQTT: embedded MQTT broker used in this demo (`amqtt`)
- asyncua: OPC UA Python communication (`asyncua`, sync wrapper `asyncua.sync`)
- paho-mqtt: MQTT publishing/subscribing in Python (`paho-mqtt`)
- MQTT.js: browser MQTT client (`mqtt.js`)
- Chart.js: plotting library in the web dashboard

## Roadmap / TODO (community-friendly)

- [ ] Test MQTT auth / credentials end-to-end (broker + clients)
- [ ] Test against a real PLC (not only simulation)
- [ ] Add more GVL folders/symbols and re-browse + re-test the bridge
- [ ] Harden MQTT transport (TLS if you choose to expose beyond localhost)

## License

MIT License (see `LICENSE`).
