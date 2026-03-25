# OPC UA → MQTT demo (Python)

Self-contained proof-of-concept: **CODESYS OPC UA server** → **Python bridge** → **embedded MQTT broker** → **web dashboard** or **terminal/GUI MQTT clients**.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy config.default.json config.json   # or let run.py create it
python run.py
```

- Dashboard: http://127.0.0.1:5050/
- Admin: http://127.0.0.1:5050/admin

Other clients (with `run.py` running):

```bash
python mqtt_sim_client.py          # terminal log
python mqtt_gui_client.py          # tkinter + matplotlib plots + export
```

See **README.txt** for full detail (WebSocket URL, browse OPC, etc.).

## What’s in the box

| Piece | Role |
|--------|------|
| `run.py` | Starts embedded **aMQTT** broker, OPC→MQTT bridge, **Flask** UI |
| `opc_bridge.py` | OPC UA polling → JSON on MQTT topics `opc/<id>` |
| `broker_config.yaml` | Broker TCP `1883`, WebSocket `9001` (localhost) |
| `mqtt_gui_client.py` | Desktop plot + CSV/JSON export (MQTT TCP) |
| `mqtt_sim_client.py` | Minimal subscriber (stdout) |

## Git

This folder can be its own repository (`git init` here). Ignore local `config.json` (see `.gitignore`).
