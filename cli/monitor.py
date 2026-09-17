"""
Security Dashboard / SOC Security Monitor CLI (`python -m cli.monitor`).

Displays live plant state, anomaly score indicator, cause analysis,
physics residuals, and real-time security advisories.
"""

import os
import sys
import time
from typing import Any, Dict

import core.config as cfg
from core.database import db
from mqtt.client import ICSCMQTTClient
import mqtt.topics as topics

latest_telemetry: Dict[str, Any] = {}
latest_alerts: list = []


def on_telemetry(topic: str, payload: Dict[str, Any]):
    global latest_telemetry
    latest_telemetry = payload


def on_alert(topic: str, payload: Dict[str, Any]):
    global latest_alerts
    latest_alerts.append(payload)


def render_dashboard():
    os.system("clear" if os.name == "posix" else "cls")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║             ICSC PROCESS-AWARE SECURITY MONITOR                ║")
    print("╠════════════════════════════════════════════════════════════════╣")

    t = dict(latest_telemetry)
    if not t:
        print("║ Status: WAITING FOR TELEMETRY STREAM...                        ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        return

    lvl = t.get("level", 0.0)
    press = t.get("pressure", 0.0) / 1000.0
    pump = t.get("pump_pct", 0.0) * 100.0
    valve = t.get("valve_pct", 0.0) * 100.0
    inflow = t.get("inflow", 0.0)
    outflow = t.get("outflow", 0.0)
    mode = t.get("operating_mode", "RUNNING")

    # Get latest alert anomaly score
    recent_alerts = db.get_recent_alerts(limit=10)
    latest_score = recent_alerts[0]["anomaly_score"] if recent_alerts else 0.0
    status_str = "NORMAL"
    if latest_score > cfg.SCORE_WARNING_MAX:
        status_str = "CRITICAL ANOMALY"
    elif latest_score > cfg.SCORE_WATCH_MAX:
        status_str = "WARNING"
    elif latest_score > cfg.SCORE_NORMAL_MAX:
        status_str = "WATCH"

    blocked_count = db.get_blocked_attacks_count()
    ips_mode_str = f"IPS Mode: [{cfg.SECURITY_MODE}]"

    print(f"║ Plant: TANK-01   | Mode: {mode:9s} | {ips_mode_str:22s} ║")
    print(f"║ Security Status: {status_str:16s} | Attacks Blocked: {blocked_count:<5d} ║")
    print("╠════════════════════════════════════════════════════════════════╣")
    print(f"║ Level       : {lvl:6.3f} m   (Safe envelope: 0.10 m - 0.90 m)       ║")
    print(f"║ Pressure    : {press:6.2f} kPa (Ceiling: 8.83 kPa)                  ║")
    print(f"║ Pump        : {pump:5.1f} %    | Valve      : {valve:5.1f} %               ║")
    print(f"║ Inflow      : {inflow:6.3f} m³/s| Outflow    : {outflow:6.3f} m³/s           ║")
    print("╠════════════════════════════════════════════════════════════════╣")

    # Render Anomaly Score Bar
    bar_len = 30
    filled = int(latest_score * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"║ Anomaly Score: [{bar}] {latest_score:4.2f} / 1.00            ║")
    print("╠════════════════════════════════════════════════════════════════╣")
    print("║ RECENT SECURITY ADVISORIES & INTERLOCKS (Last 5):               ║")

    for a in recent_alerts[:5]:
        sev = a["severity"]
        what = a["what_happened"]
        score = a["anomaly_score"]
        print(f"║ • [{sev:8s}] (Score {score:.2f}) {what[:42]:42s} ║")

    if not recent_alerts:
        print("║ • No security advisories raised. Process nominal.             ║")

    print("╚════════════════════════════════════════════════════════════════╝")


def main():
    mqtt_client = ICSCMQTTClient(client_id="security-dashboard")
    mqtt_client.subscribe(topics.TOPIC_TELEMETRY, on_telemetry)
    mqtt_client.subscribe(topics.LEGACY_TOPIC_TELEMETRY, on_telemetry)
    mqtt_client.subscribe(topics.TOPIC_ALERTS, on_alert)
    mqtt_client.subscribe(topics.LEGACY_TOPIC_ALERTS, on_alert)
    mqtt_client.connect()

    print("[*] Starting Security Monitor Dashboard...")
    try:
        while True:
            render_dashboard()
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[*] Monitor closed.")
    finally:
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
