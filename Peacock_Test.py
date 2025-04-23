#!/usr/bin/env python3
import subprocess
import time
import datetime
import re

def fetch_server_list():
    # Ruft die komplette Serverliste von NordVPN ab und filtert per jq alle US-Server heraus,
    # wobei er nur die Felder id, name, station, hostname und status ausgibt.
    command = r'''curl -s "https://api.nordvpn.com/v2/servers?limit=0" | jq -r '.servers[] | select(.hostname | startswith("us")) | {id, name, station, hostname, status} | "\(.id)\t\(.name)\t\(.station)\t\(.hostname)\t\(.status)"' '''
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout

def connect_vpn(hostname):
    print(f"Verbinde mit {hostname} ...")
    result = subprocess.run(["nordvpn", "connect", hostname], capture_output=True, text=True)
    output = result.stdout.strip()
    print(output)
    # Prüfe auf dedizierte IP-Anforderung
    if "dedicated ip" in output.lower():
        return "dedicated"
    # Prüfe, ob die Verbindung fehlgeschlagen ist
    if "connection has failed" in output.lower():
        return "failed"
    return "connected"

def disconnect_vpn():
    result = subprocess.run(["nordvpn", "disconnect"], capture_output=True, text=True)
    print(result.stdout.strip())
    return result.returncode

def check_external_ip():
    """
    Ruft mittels curl die externe IP ab (z. B. via ip.me).
    """
    result = subprocess.run(["curl", "-s", "ip.me"], capture_output=True, text=True)
    return result.stdout.strip()

def check_peacock():
    # Ermittelt mit curl die finale URL, die Peacock zurückliefert.
    curl_proc = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{url_effective}", "-L", "https://www.peacocktv.com"],
        capture_output=True, text=True
    )
    effective_url = curl_proc.stdout.strip()
    return effective_url

def main():
    # Heutiges Datum im Format YYYYMMDD
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    # Standard-Dateiname für die Serverliste: NordVPN_US_<Datum>.txt
    default_server_file = f"NordVPN_US_{today}.txt"
    input_file = input(f"Bitte Dateinamen für die Serverliste eingeben (Standard: {default_server_file}): ").strip()
    if not input_file:
        input_file = default_server_file

    print("Hole die Serverliste von NordVPN ...")
    server_list_data = fetch_server_list()
    if not server_list_data:
        print("Fehler: Es konnten keine Daten abgerufen werden.")
        return
    # Speichern der Serverliste
    with open(input_file, "w") as f:
        f.write(server_list_data)
    print(f"Serverliste wurde in '{input_file}' gespeichert.")
    
    # Standard-Dateiname für die Ergebnisse: Peacock_Results_<Datum>.txt
    default_results_file = f"Peacock_Results_{today}.txt"
    output_file = input(f"Bitte Dateinamen für die Ergebnisse eingeben (Standard: {default_results_file}): ").strip()
    if not output_file:
        output_file = default_results_file
    
    # Ergebnisse-Datei initialisieren (jetzt mit zusätzlicher Spalte für External IP)
    with open(output_file, "w") as f:
        f.write("Hostname\tExternal IP\tErgebnis\n")
    
    # Lese die Serverliste ein – erwartet Tab-getrennte Felder:
    # id<TAB>name<TAB>station<TAB>hostname<TAB>status
    with open(input_file, "r") as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            print(f"Zeile hat nicht genügend Felder: {line}")
            continue

        # Der Hostname ist das 4. Feld (Index 3)
        hostname_full = parts[3]
        # Entferne den Suffix ".nordvpn.com", sodass z. B. "us5063" übrig bleibt
        hostname = hostname_full.replace(".nordvpn.com", "")
        
        print(f"\nStarte Test für {hostname} ...")
        connection_status = connect_vpn(hostname)
        
        if connection_status == "dedicated":
            result = "Skipped (Dedicated IP required)"
            print(f"{hostname}\t{result}")
            ext_ip = "n/a"
        elif connection_status == "failed":
            result = "Skipped (VPN connection failed)"
            print(f"{hostname}\t{result}")
            ext_ip = "n/a"
        elif connection_status == "unavailable":
            result = "Skipped (Server unavailable or unsupported)"
            print(f"{hostname}\t{result}")
            ext_ip = "n/a"
        else:
            # Warte, damit sich die VPN-Verbindung aufbauen kann
            time.sleep(5)
            # Hole zuerst die externe IP
            ext_ip = check_external_ip()
            print(f"Externe IP: {ext_ip}")
            # Prüfe den Zugriff auf Peacock
            effective_url = check_peacock()
            if "/unavailable" in effective_url:
                result = "Blocked"
            else:
                result = "Available"
            print(f"{hostname}\t{result}")
        
        # Ergebnis in die Ergebnisdatei schreiben
        with open(output_file, "a") as f:
            f.write(f"{hostname}\t{ext_ip}\t{result}\n")
        
        disconnect_vpn()
        # Kurze Pause vor dem nächsten Test
        time.sleep(2)
    
    print(f"\nTest abgeschlossen. Ergebnisse wurden in '{output_file}' gespeichert.")

if __name__ == "__main__":
    main()

