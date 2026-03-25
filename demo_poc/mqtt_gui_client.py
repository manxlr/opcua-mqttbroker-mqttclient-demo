"""
Desktop MQTT subscriber with live plots and export (same idea as the web dashboard).

Uses MQTT TCP (port 1883) like mqtt_sim_client.py — not WebSocket.

Run (with the demo broker running):

    .\\venv\\Scripts\\python demo_poc\\mqtt_gui_client.py
"""

from __future__ import annotations

import csv
import json
import random
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Match dashboard-ish colors
_PALETTE = ("#2ef2ff", "#ff2ecb", "#7cff7c", "#ffd000", "#b388ff", "#ff9f43")


class MqttGuiApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("MQTT live plot · OPC demo")
        self.root.minsize(880, 560)
        try:
            plt.style.use("dark_background")
        except Exception:
            pass

        self._client: mqtt.Client | None = None
        self._lock = threading.Lock()
        self._series: dict[str, dict[str, Any]] = {}
        self._redraw_pending = False
        self._max_points = tk.IntVar(value=2000)

        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Host").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        self._host = tk.StringVar(value="127.0.0.1")
        ttk.Entry(top, textvariable=self._host, width=14).grid(row=0, column=1, padx=4)

        ttk.Label(top, text="Port").grid(row=0, column=2, sticky=tk.W, padx=(8, 4))
        self._port = tk.StringVar(value="1883")
        ttk.Entry(top, textvariable=self._port, width=6).grid(row=0, column=3, padx=4)

        ttk.Label(top, text="Topic").grid(row=0, column=4, sticky=tk.W, padx=(8, 4))
        self._topic = tk.StringVar(value="opc/#")
        ttk.Entry(top, textvariable=self._topic, width=22).grid(row=0, column=5, padx=4)

        ttk.Label(top, text="Max pts").grid(row=0, column=6, sticky=tk.W, padx=(8, 4))
        ttk.Spinbox(top, from_=100, to=50_000, textvariable=self._max_points, width=7).grid(
            row=0, column=7, padx=4
        )

        self._btn_connect = ttk.Button(top, text="Connect", command=self._connect)
        self._btn_connect.grid(row=0, column=8, padx=8)
        ttk.Button(top, text="Disconnect", command=self._disconnect).grid(row=0, column=9, padx=4)

        btn_row = ttk.Frame(self.root, padding=(8, 0))
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Export CSV…", command=self._export_csv).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Export JSON…", command=self._export_json).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Clear plot", command=self._clear).pack(side=tk.LEFT, padx=4)
        self._status = tk.StringVar(value="Disconnected")
        ttk.Label(btn_row, textvariable=self._status).pack(side=tk.RIGHT, padx=12)

        self._fig = Figure(figsize=(9, 4.5), dpi=100)
        self._ax = self._fig.add_subplot(111)
        self._ax.set_xlabel("Time (ms)")
        self._ax.set_ylabel("Value")
        self._ax.grid(True, alpha=0.25)

        plot_frame = ttk.Frame(self.root, padding=8)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        self._canvas = FigureCanvasTkAgg(self._fig, master=plot_frame)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        values = ttk.LabelFrame(self.root, text="Latest values", padding=6)
        values.pack(fill=tk.BOTH, padx=8, pady=(0, 8))
        self._value_text = tk.Text(values, height=5, wrap=tk.WORD, state=tk.DISABLED)
        self._value_text.pack(fill=tk.BOTH, expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _append_point(self, topic: str, ts: float, y: float) -> None:
        mx = max(50, int(self._max_points.get()))
        with self._lock:
            if topic not in self._series:
                self._series[topic] = {"x": [], "y": []}
            s = self._series[topic]
            s["x"].append(ts)
            s["y"].append(y)
            while len(s["x"]) > mx:
                s["x"].pop(0)
                s["y"].pop(0)

    def _redraw(self) -> None:
        self._ax.clear()
        self._ax.grid(True, alpha=0.25)
        self._ax.set_xlabel("Time (ms)")
        self._ax.set_ylabel("Value")
        with self._lock:
            items = list(self._series.items())
        for i, (topic, s) in enumerate(sorted(items)):
            color = _PALETTE[i % len(_PALETTE)]
            if s["x"]:
                self._ax.plot(s["x"], s["y"], label=topic, color=color, linewidth=1.5)
        if items:
            self._ax.legend(loc="upper left", fontsize=8)
        self._canvas.draw_idle()

        # Latest values panel
        lines = []
        with self._lock:
            for topic in sorted(self._series):
                sy = self._series[topic]["y"]
                if sy:
                    lines.append(f"{topic}  →  {sy[-1]}")
        self._value_text.config(state=tk.NORMAL)
        self._value_text.delete("1.0", tk.END)
        self._value_text.insert(tk.END, "\n".join(lines) if lines else "(no data)")
        self._value_text.config(state=tk.DISABLED)

    def _schedule_redraw(self) -> None:
        if self._redraw_pending:
            return
        self._redraw_pending = True

        def _go() -> None:
            self._redraw_pending = False
            self._redraw()

        self.root.after(0, _go)

    def _on_message(self, _c: mqtt.Client, _u: object, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        ts = payload.get("ts")
        val = payload.get("value")
        if ts is None:
            return
        try:
            y = float(val) if not isinstance(val, bool) else float(int(val))
        except (TypeError, ValueError):
            return
        self._append_point(msg.topic, float(ts), y)
        self._schedule_redraw()

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: object,
        _flags: dict[str, Any],
        reason_code: mqtt.ReasonCode,
        _props: object,
    ) -> None:
        if reason_code.is_failure:
            self.root.after(0, lambda: self._status.set(f"Connect failed: {reason_code}"))
            return
        topic = self._topic.get().strip() or "opc/#"

        def do_sub() -> None:
            client.subscribe(topic, qos=0)
            self._status.set(f"Connected · {topic}")

        self.root.after(0, do_sub)

    def _connect(self) -> None:
        self._disconnect()
        host = self._host.get().strip() or "127.0.0.1"
        try:
            port = int(self._port.get().strip() or "1883")
        except ValueError:
            messagebox.showerror("Port", "Invalid port")
            return
        cid = f"gui_{random.randint(0, 99999)}"
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        try:
            self._client.connect(host, port, keepalive=60)
        except Exception as e:
            messagebox.showerror("MQTT", str(e))
            self._client = None
            return
        self._client.loop_start()
        self._status.set("Connecting…")

    def _disconnect(self) -> None:
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._status.set("Disconnected")

    def _clear(self) -> None:
        with self._lock:
            self._series.clear()
        self._redraw()

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
        )
        if not path:
            return
        with self._lock, open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["topic", "t_ms", "value"])
            for topic in sorted(self._series):
                for t, y in zip(
                    self._series[topic]["x"],
                    self._series[topic]["y"],
                    strict=False,
                ):
                    w.writerow([topic, t, y])
        messagebox.showinfo("Export", "Saved.")

    def _export_json(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
        )
        if not path:
            return
        with self._lock:
            out = {
                topic: [{"t": a, "y": b} for a, b in zip(s["x"], s["y"], strict=False)]
                for topic, s in self._series.items()
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        messagebox.showinfo("Export", "Saved.")

    def _on_close(self) -> None:
        self._disconnect()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    MqttGuiApp().run()


if __name__ == "__main__":
    main()
