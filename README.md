# CODESYS OPC UA -> MQTT -> Real-time Dashboard (Community Demo)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#)
[![OPC UA](https://img.shields.io/badge/OPC%20UA-Client%2FServer-brightgreen)](#)
[![MQTT](https://img.shields.io/badge/MQTT-PubSub-brightgreen)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## Overview

This repository is a community-friendly proof-of-concept pipeline:

1. CODESYS PLC exposes variables via OPC UA
2. A Python bridge reads OPC UA nodes and publishes JSON messages to MQTT
3. An embedded MQTT broker (aMQTT) serves MQTT to multiple clients
4. A Flask web UI subscribes over MQTT (WebSocket) and plots live charts
5. Optional MQTT clients (terminal + desktop GUI) subscribe and plot/export

## Screenshots

These PNGs are included in `Screenshots/`.

- Dashboard: `Screenshots/OPC_UA_and_MQTT_BROKER_Dashboard.png`
- Admin browse page: `Screenshots/OPC_UA_and_MQTT_BROKER_Admin_Page.png`
- Variable selection (CODESYS): `Screenshots/OPC_UA_Variables_Selection_CODESYS.png`
- MQTT client (terminal): `Screenshots/MQTT_Client.png`

(Optionally add more screenshots, plus:
- `Screenshots/flow-diagram.png`
- `Screenshots/repo-icon.png`)

## Architecture (high level)

```mermaid
flowchart LR
  subgraph plc[CODESYS]
    srv[OPC UA Server :4840]
  end

  subgraph bridge[Python Bridge]
    cli[OPC UA Client (asyncua.sync)]
    pub[Publish JSON to MQTT]
  end

  subgraph broker[aMQTT Broker]
    tcp[MQTT TCP 1883]
    ws[MQTT WebSocket 9001]
  end

  subgraph ui[MQTT Clients]
    web[Flask Dashboard (MQTT over WS)]
    term[Terminal Simulator]
    gui[Desktop GUI Plots]
  end

  srv --> cli --> pub --> ws --> web
  pub --> tcp --> term
  pub --> tcp --> gui
```

## Default endpoints / topic format

- OPC UA server (used by the Python bridge): `opc.tcp://localhost:4840`
- Embedded MQTT broker (in this demo):
  - MQTT TCP: `127.0.0.1:1883`
  - MQTT WebSocket (browser): `127.0.0.1:9001`
- MQTT topics published by the bridge:
  - `opc/<signal_id>`
- Example JSON payload:
  - {"ts": 1710000000000, "id": "lrAxisPosition", "node_id": "ns=4;s=...", "value": 12.34}

## 1) CoDeSys Project Setup

Copy/paste instructions for the CoDeSys OPC UA server example.

1. Download/obtain the original project from this repository's included `CoDeSys/` folder.
2. Open Project: Open the `CoDeSys_Projects/OPC-UA_Server Example Project - Start.project` in your CoDeSys Development System.
   - This project contains a simple program (`PLC_PRG`) controlling a virtual SoftMotion axis (`Axis1`) and a Global Variable List (`OPC_GVL`) to hold data for OPC UA.
3. (Follow Video for Setup): The video tutorial walks through these steps using the Start project:
   - Symbol Configuration: Adding a 'Symbol Configuration' object, building the project, selecting `GVL_AxisData` (or specific variables inside it) for exposure, and enabling "Support OPC UA features".
   - Disable OPC UA Authentication: Double-clicking 'Device', going to the 'Communication Settings' tab, clicking on 'Device', and then on 'Change Runtime Security Policy' checking 'Allow anonymous login'. Note the endpoint URL (usually `opc.tcp://localhost:4840`).
   - Reference Project: `OPC-UA_Server Example Project - Complete.project` has the Symbol Configuration and OPC UA server already set up for comparison.
4. Run Simulation:
   - Start the local PLC (Right Click on CoDeSys tray -> Start PLC).
   - Login (Online -> Login).
   - Create user authentication and login if prompted.
   - Download the project if prompted.
   - Start the PLC (Debug -> Start or F5).
   - You can manually toggle variables like `StartButton` or `StopButton` in `PLC_PRG` to see the simulated axis move and `GVL_AxisData.lrAxisPosition` update.

Note: the device name string inside your NodeIds may differ from the simulation default. Use the admin page's browse feature to pick the correct NodeIds.

## 2) Run the demo (Flask + embedded broker + OPC->MQTT bridge)

1. Create venv + install dependencies

```bash
python -m venv .venv
.
.venv\Scripts\activate
pip install -r requirements-demo.txt
```

2. Start the demo

```bash
python demo_poc\run.py
```

3. Open the UI

- Dashboard: http://127.0.0.1:5050/
- Bridge admin: http://127.0.0.1:5050/admin

On the dashboard:
- WebSocket URL: ws://127.0.0.1:9001
- Subscribe pattern: opc/#

On the admin page:
- Use "Fetch variables from OPC (browse)" and then "Save & restart bridge".

## 3) MQTT client options

With the demo running:

### Terminal MQTT simulator

```bash
python demo_poc\mqtt_sim_client.py
```

### Desktop GUI (plots + export)

```bash
python demo_poc\mqtt_gui_client.py
```

Both subscribe to MQTT TCP `127.0.0.1:1883` and default topic filter `opc/#`.

## Image generation prompts (for community polish)

You can generate the following PNGs and place them in `Screenshots/`:

1. Flow diagram
   - Filename: `Screenshots/flow-diagram.png`
   - Prompt:
     "Create a clean modern vector-style flow diagram (transparent background) showing 'CODESYS PLC (OPC UA server) -> Python OPC UA bridge -> Embedded MQTT broker (aMQTT) -> MQTT clients (Flask dashboard via WebSocket, Terminal sim, Desktop GUI plots)'. Include small icon-like boxes for OPC UA, Python, MQTT, Flask, and charts. Use a dark theme with neon cyan/pink accents. Add short labels: 'opc.tcp://localhost:4840', 'MQTT TCP 1883', 'MQTT WS 9001', and topics 'opc/<signal_id>'. Ensure it looks good at 1400x800, readable fonts, and no tiny text."

2. Repository icon
   - Filename: `Screenshots/repo-icon.png`
   - Prompt:
     "Design a single square repository icon (transparent background) with a glass-neon aesthetic: a combined OPC UA + MQTT symbol. Use a simple abstract node graph or two connected endpoints. Add neon cyan outline and a magenta accent. Include minimal text-free design so it scales well. Output at 512x512."

## Acknowledgements / Credits

This community demo is inspired by:
- https://github.com/mn-automation-academy/tutorial-codesys-opc-ua-with-python

Additional technologies used:
- aMQTT (embedded broker)
- asyncua (OPC UA client sync wrapper: asyncua.sync)
- paho-mqtt (MQTT publish/subscribe)
- mqtt.js + Chart.js (web dashboard)

## Roadmap / TODO

- [ ] Test MQTT auth / credentials end-to-end (broker + clients)
- [ ] Test on real PLC hardware (not only simulation)
- [ ] Add more GVL folders/symbols, re-browse and re-test the bridge
- [ ] Harden MQTT transport (TLS if you expose beyond localhost)

## License

MIT License (see `LICENSE`).
