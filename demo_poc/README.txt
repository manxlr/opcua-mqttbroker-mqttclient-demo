OPC → MQTT glass dashboard (POC)
================================

Explain it like you're 5
------------------------
- **The PLC (CODESYS)** is a box that *knows* your variables (position, speed, …).
- **OPC UA** is a *language* so programs can ask that box: "what is the value now?"
- **Flask** is just a small *website + control panel* on your PC. It is **not** the MQTT broker.
  It shows the admin page and the pretty dashboard, and it *starts* the other pieces.
- **The MQTT broker** (aMQTT inside this demo) is a *mailroom*: publishers drop messages on
  *topics*, subscribers pick topics they care about. It listens on **1883** (TCP) and **9001**
  (WebSocket for browsers).
- **The OPC bridge** (Python thread) reads OPC, then *publishes* JSON to MQTT topics like
  `opc/lrAxisPosition`. So: PLC → OPC → Python → MQTT broker → (any client).

Hardcoded variables?
--------------------
The *default* config lists three axis variables so the demo works out of the box. You can:

- Use **/admin → "Fetch variables from OPC (browse)"**: set the **parent folder** NodeId
  (default: `GVL_AxisData`), click **Browse**, then **Add** or **Add all variables to signals**.
- Or paste NodeIds from UaExpert like before.

Second client (terminal simulator)
----------------------------------
With `demo_poc\run.py` already running, open another terminal:

    .\venv\Scripts\python demo_poc\mqtt_sim_client.py

It connects to **mqtt://127.0.0.1:1883** and prints the same JSON the browser sees.
That proves another app can consume the broker without OPC or Flask.

Desktop GUI (plots + CSV/JSON like the web dashboard)
-------------------------------------------------------
Requires `matplotlib` (included in `requirements-demo.txt`).

    .\venv\Scripts\python demo_poc\mqtt_gui_client.py

Connect to host **127.0.0.1** port **1883**, topic **opc/#**. Use Export or Clear like the browser.

Prerequisites
-------------
- CODESYS OPC UA server running (sim or PLC), anonymous / SecurityPolicy None as in your project.
- Python venv at project root with dependencies installed:

    .\venv\Scripts\pip install -r requirements-demo.txt

Run
---
From the OPC project folder (parent of demo_poc):

    .\venv\Scripts\python demo_poc\run.py

- Dashboard:  http://127.0.0.1:5050/
- Bridge admin: http://127.0.0.1:5050/admin

Embedded broker (aMQTT) listens on:
- MQTT TCP: 127.0.0.1:1883  (Python OPC bridge publishes here)
- WebSocket: 127.0.0.1:9001 (browser dashboard uses mqtt.js)

WebSocket URL (dashboard)
-------------------------
The browser cannot speak raw MQTT TCP (port 1883). It uses MQTT over WebSocket on port 9001.
Set: ws://127.0.0.1:9001

That is NOT the OPC server URL. OPC UA stays opc.tcp://localhost:4840 for the Python bridge
(see /admin). The dashboard only talks to the embedded MQTT broker.

Poll interval (OPC acquisition)
---------------------------------
Default in config is 2000 ms (2 s) to limit load and console noise. Change "Poll interval (ms)"
on /admin or edit config.json.

On the dashboard, click Connect with default WebSocket URL ws://127.0.0.1:9001 and subscribe pattern opc/#

Edit OPC NodeIds in /admin if your runtime device name differs from "CODESYS Control Win V3 x64".

To expose the broker on your LAN, edit demo_poc/broker_config.yaml bind addresses (not recommended without authentication).
