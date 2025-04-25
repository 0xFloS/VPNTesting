#!/usr/bin/env python3
import subprocess
import datetime
import re
import time

def get_server_list():
    """Ruft die komplette Serverliste über 'expressvpn list all' ab."""
    result = subprocess.run(["expressvpn", "list", "all"], capture_output=True, text=True)
    return result.stdout

def parse_us_server_list(output):
    """
    Parst die Ausgabe von 'expressvpn list all'. Erwartet werden Zeilen mit
    mindestens 3 oder 4 Spalten, getrennt durch mindestens zwei Leerzeichen.
    
    Beispielzeile:
      uswd  United States (US)          USA - Washington DC            Y
    
    Es werden nur Zeilen ausgewertet, deren Location den String "USA -" enthält.
    Liefert eine Liste von Dictionaries mit den Keys:
      - code: Server-Code (z. B. uswd)
      - country: z. B. "United States (US)" (kann auch leer sein)
      - location: z. B. "USA - Washington DC"
    """
    parsed = []
    lines = output.strip().splitlines()
    for line in lines:
        if not line.strip():
            continue
        # Teile die Zeile an Stellen, wo mindestens zwei Leerzeichen stehen
        parts = re.split(r'\s{2,}', line)
        if len(parts) == 4:
            code, country, location, _ = parts
        elif len(parts) == 3:
            code, location, _ = parts
            country = ""
        else:
            continue  # Zeile entspricht nicht dem erwarteten Format
        # Nur US-Server übernehmen
        if "USA -" in location:
            parsed.append({
                "code": code,
                "country": country,
                "location": location
            })
    return parsed

def save_server_list(parsed, filename):
    """Speichert die geparste Serverliste in eine Datei (Tab-getrennt)."""
    with open(filename, "w") as f:
        for server in parsed:
            f.write(f"{server['code']}\t{server['country']}\t{server['location']}\n")

def connect_vpn(location):
    """
    Baut die VPN-Verbindung auf.
    Der Verbindungsbefehl lautet: 
      expressvpn connect "<Location>"
    """
    print(f"Connecting to {location} ...")
    subprocess.run(["expressvpn", "connect", location], capture_output=True, text=True)
    # Warte einige Sekunden, damit sich die Verbindung stabilisiert (anpassen, falls nötig)
    time.sleep(8)

def disconnect_vpn():
    """Trennt die aktuelle VPN-Verbindung."""
    subprocess.run(["expressvpn", "disconnect"], capture_output=True, text=True)
    print("Disconnected VPN")
    time.sleep(3)

def check_external_ip():
    """Fragt per curl die externe IP ab (mittels curl ip.me)."""
    result = subprocess.run(["curl", "-s", "ip.me"], capture_output=True, text=True)
    return result.stdout.strip()

def check_peacock():
    """
    Ruft mit curl die finale URL von https://www.peacocktv.com ab.
    Wird in der effektiven URL der Pfad '/unavailable' gefunden, gilt Peacock als blockiert.
    """
    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{url_effective}", "-L", "https://www.peacocktv.com"],
        capture_output=True, text=True
    )
    effective_url = result.stdout.strip()
    return effective_url

def main():
    # Heutiges Datum im Format YYYYMMDD
    today = datetime.datetime.now().strftime("%Y%m%d")
    server_filename = f"expressvpn_us_server_list_{today}.txt"
    result_filename = f"Peacock_Results_ExpressVPN_{today}.txt"

    # 1. Serverliste abrufen und US-Server filtern
    print("Fetching server list with 'expressvpn list all' ...")
    output = get_server_list()
    if not output:
        print("Error: No server list received.")
        return
    us_servers = parse_us_server_list(output)
    if not us_servers:
        print("Keine US-Server gefunden.")
        return
    save_server_list(us_servers, server_filename)
    print(f"US server list saved in '{server_filename}'")

    # Ergebnisse-Datei initialisieren
    with open(result_filename, "w") as f:
        f.write("Location\tServer Code\tExternal IP\tPeacock Result\n")
    
    # 2. Für jeden US-Server testen:
    for server in us_servers:
        location = server["location"]
        code = server["code"]
        print(f"\nTesting server {code} - {location}")
        
        connect_vpn(location)
        ext_ip = check_external_ip()
        print(f"External IP: {ext_ip}")
        
        effective_url = check_peacock()
        if "/unavailable" in effective_url:
            result_text = "Blocked"
        else:
            result_text = "Available"
        print(f"Peacock: {result_text}")
        
        # Ergebnis abspeichern
        with open(result_filename, "a") as f:
            f.write(f"{location}\t{code}\t{ext_ip}\t{result_text}\n")
        
        disconnect_vpn()
    
    print(f"\nAll tests completed. Results saved in '{result_filename}'")

if __name__ == "__main__":
    main()

