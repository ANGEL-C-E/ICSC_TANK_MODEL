"""
Attacker Interactive CLI (`python -m cli.attacker`).

Demonstrates realistic cyber-attack execution against the vulnerable backend API path.
Exploits authorization bypass flaw (/api/vulnerable_control) to issue syntactically valid
control commands without holding elevated operator privileges.
"""

import sys
import time

from backend.api import BackendAPI
from control.command_gateway import CommandGateway
from mqtt.client import ICSCMQTTClient


def main():
    mqtt_client = ICSCMQTTClient(client_id="attacker-cli")
    mqtt_client.connect()

    gateway = CommandGateway(mqtt_client)
    api = BackendAPI(gateway)

    print("╔════════════════════════════════════════════╗")
    print("║          REMOTE ACCESS TERMINAL            ║")
    print("╚════════════════════════════════════════════╝")
    print("Target:     ICS Control Backend (/api/vulnerable_control)")
    print("Connection: Established\n")

    # Authenticate as low-privileged guest user 'attacker_01'
    print("[*] Authenticating with low-privilege guest credentials (attacker_01)...")
    ok, msg, auth_res = api.login("attacker_01", "guest")
    if not ok:
        print(f"[!] Authentication failed: {msg}")
        mqtt_client.disconnect()
        sys.exit(1)

    guest_token = auth_res["token"]
    print(f"[+] Authenticated as: {auth_res['username']} (Role: {auth_res['role']})")
    print("[*] Type `exploit` to trigger authorization bypass or issue control commands.\n")

    is_exploited = False

    try:
        while True:
            line = input("attacker> ").strip()
            if not line:
                continue

            cmd_lower = line.lower()
            if cmd_lower in ("quit", "exit"):
                break

            if cmd_lower in ("exploit", "exploit backend_auth"):
                print("[*] Probing backend endpoint for authorization boundary flaws...")
                time.sleep(0.5)
                print("[*] Vulnerable endpoint discovered: /api/vulnerable_control")
                print("[+] Authorization bypass verified. Guest session upgraded for control access.")
                is_exploited = True
                continue

            if not is_exploited:
                # Attempting direct execution will fail due to RBAC
                ok, response_msg, _ = api.submit_command(guest_token, line)
                if not ok:
                    print(f"[!] Direct gateway request blocked: {response_msg}")
                    print("[!] Hint: Type `exploit` to route commands through the vulnerable backend path.")
                else:
                    print(f"[+] Command executed: {response_msg}")
            else:
                # Executing command through vulnerable backend route
                ok, response_msg, _ = api.submit_vulnerable_command(guest_token, line)
                if ok:
                    print(f"[+] Command submitted via exploit: {response_msg}")
                else:
                    print(f"[!] Exploit command failed: {response_msg}")

    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        mqtt_client.disconnect()
        print("[*] Attacker terminal closed.")


if __name__ == "__main__":
    main()
