"""Flask app: dashboard, admin API, static assets."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from demo_poc.opc_bridge import DEFAULT_BROWSE_PARENT, OpcMqttBridge, opc_browse_children, opc_test_read

BASE_DIR = Path(__file__).resolve().parent


def create_app(
    *,
    config_path: Path | None = None,
    bridge: OpcMqttBridge | None = None,
) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
        static_url_path="/static",
    )
    app.config["CONFIG_PATH"] = Path(config_path) if config_path else BASE_DIR / "config.json"
    app.config["BRIDGE"] = bridge

    @app.route("/")
    def dashboard() -> str:
        return render_template("dashboard.html")

    @app.route("/admin")
    def admin() -> str:
        return render_template("admin.html")

    @app.get("/api/config")
    def api_config_get() -> Any:
        path: Path = app.config["CONFIG_PATH"]
        if not path.is_file():
            return jsonify({"error": "config missing"}), 404
        with path.open(encoding="utf-8") as f:
            return jsonify(json.load(f))

    @app.post("/api/config")
    def api_config_post() -> Any:
        path: Path = app.config["CONFIG_PATH"]
        data = request.get_json(force=True, silent=False)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "JSON object required"}), 400
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        _restart_bridge(app)
        return jsonify({"ok": True})

    @app.post("/api/bridge/restart")
    def api_bridge_restart() -> Any:
        _restart_bridge(app)
        return jsonify({"ok": True})

    @app.post("/api/opc/test")
    def api_opc_test() -> Any:
        body = request.get_json(force=True, silent=True) or {}
        opc_url = body.get("opc_url")
        node_id = body.get("node_id")
        if not opc_url or not node_id:
            return jsonify({"ok": False, "error": "opc_url and node_id required"}), 400
        return jsonify(opc_test_read(str(opc_url), str(node_id)))

    @app.post("/api/opc/browse")
    def api_opc_browse() -> Any:
        body = request.get_json(force=True, silent=True) or {}
        opc_url = body.get("opc_url")
        raw_parent = body.get("parent_node_id")
        if not raw_parent or not str(raw_parent).strip():
            parent_node_id = DEFAULT_BROWSE_PARENT
        else:
            parent_node_id = str(raw_parent).strip()
        if not opc_url:
            return jsonify({"ok": False, "error": "opc_url required"}), 400
        return jsonify(opc_browse_children(str(opc_url), str(parent_node_id)))

    @app.get("/api/bridge/status")
    def api_bridge_status() -> Any:
        br: OpcMqttBridge | None = app.config.get("BRIDGE")
        if br is None:
            return jsonify({"running": False, "last_error": None})
        return jsonify({"running": True, "last_error": br.last_error})

    return app


def _restart_bridge(app: Flask) -> None:
    br: OpcMqttBridge | None = app.config.get("BRIDGE")
    if br is None:
        return
    br.stop()
    br.start()


def ensure_config_file(config_path: Path, default_path: Path) -> None:
    if not config_path.is_file() and default_path.is_file():
        shutil.copy(default_path, config_path)
