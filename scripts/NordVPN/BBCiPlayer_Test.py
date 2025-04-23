#!/usr/bin/env python3
import subprocess
import time
import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def fetch_uk_server_list():
    """
    Ruft die UK-Serverliste von NordVPN ab und filtert alle Server heraus, deren Hostname mit "uk" beginnt.
    Liefert als Tab-getrennte Zeilen: id, name, station, hostname und status.
    """
    command = r'''curl -s "https://api.nordvpn.com/v2/servers?limit=0" | jq -r '.servers[] | select(.hostname | startswith("uk")) | {id, name, station, hostname, status} | "\(.id)\t\(.name)\t\(.station)\t\(.hostname)\t\(.status)"' '''
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout

def connect_vpn(server):
    """
    Versucht, sich per NordVPN mit dem übergebenen Server (z. B. "uk2242") zu verbinden.
    Gibt folgende Status zurück:
      - "dedicated" wenn der Server dedizierte IPs verlangt,
      - "failed" wenn die Verbindung allgemein fehlgeschlagen ist,
      - "unavailable" wenn der Server momentan nicht verfügbar ist oder die Einstellungen nicht unterstützt,
      - "connected" bei erfolgreicher Verbindung.
    """
    print(f"Verbinde mit {server} ...")
    result = subprocess.run(["nordvpn", "connect", server], capture_output=True, text=True)
    output = result.stdout.strip()
    print(output)
    
    low_output = output.lower()
    if "dedicated ip" in low_output:
        return "dedicated"
    if "connection has failed" in low_output:
        return "failed"
    if "the specified server is not available" in low_output:
        return "unavailable"
    return "connected"

def disconnect_vpn():
    """Trennt die aktuelle VPN-Verbindung."""
    result = subprocess.run(["nordvpn", "disconnect"], capture_output=True, text=True)
    print(result.stdout.strip())

def check_external_ip():
    """
    Ruft per curl die aktuelle externe IP-Adresse ab (mittels ip.me).
    """
    result = subprocess.run(["curl", "-s", "ip.me"], capture_output=True, text=True)
    return result.stdout.strip()

def check_bbc_iplayer():
    """
    Verwendet Selenium (Headless Chrome), um eine konkrete BBC iPlayer-Seite aufzurufen
    und prüft, ob der Blockierungshinweis angezeigt wird.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)
    
    url = "https://www.bbc.co.uk/iplayer"
    driver.get(url)
    time.sleep(5)  # Warte, bis die Seite vollständig geladen ist
    
    page_source = driver.page_source
    driver.quit()
    if "Sorry, BBC iPlayer isn’t available in your region." in page_source:
        return "Blocked"
    else:
        return "Available"

def main():
    # Heutiges Datum im Format YYYYMMDD
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    # Standard-Dateinamen für die UK-Serverliste
    default_server_file = f"NordVPN_UK_{today}.txt"
    input_file = input(f"Bitte Dateinamen für die Serverliste eingeben (Standard: {default_server_file}): ").strip()
    if not input_file:
        input_file = default_server_file

    print("Hole die UK-Serverliste von NordVPN ...")
    server_list_data = fetch_uk_server_list()
    if not server_list_data:
        print("Fehler: Es konnten keine Daten abgerufen werden.")
        return
    # Speichern der Serverliste
    with open(input_file, "w") as f:
        f.write(server_list_data)
    print(f"Serverliste wurde in '{input_file}' gespeichert.")
    
    # Standard-Dateiname für die Ergebnisse
    default_results_file = f"BBCiPlayer_Results_{today}.txt"
    output_file = input(f"Bitte Dateinamen für die Ergebnisse eingeben (Standard: {default_results_file}): ").strip()
    if not output_file:
        output_file = default_results_file
    # Ergebnisse-Datei initialisieren: drei Spalten: Server, externe IP, Ergebnis
    with open(output_file, "w") as f:
        f.write("Server\tExterne IP\tErgebnis\n")
    
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

        # Der Hostname ist das 4. Feld (Index 3), z. B. "uk2242.nordvpn.com"
        hostname_full = parts[3]
        # Entferne den Suffix ".nordvpn.com", sodass z. B. "uk2242" übrig bleibt
        server = hostname_full.replace(".nordvpn.com", "")
        
        try:
            print(f"\nStarte Test für {server} ...")
            connection_status = connect_vpn(server)
            
            if connection_status == "dedicated":
                result = "Skipped (Dedicated IP required)"
                print(f"{server}\t{result}")
                external_ip = "n/a"
            elif connection_status == "failed":
                result = "Skipped (VPN connection failed)"
                print(f"{server}\t{result}")
                external_ip = "n/a"
            elif connection_status == "unavailable":
                result = "Skipped (Server unavailable or unsupported)"
                print(f"{server}\t{result}")
                external_ip = "n/a"
            else:
                # Warte, damit sich die VPN-Verbindung aufbauen kann
                time.sleep(5)
                # Externe IP abfragen
                external_ip = check_external_ip()
                print(f"Externe IP: {external_ip}")
                # BBC iPlayer testen
                result = check_bbc_iplayer()
                print(f"{server}\t{external_ip}\t{result}")
            
            # Ergebnis in die Ergebnisdatei schreiben
            with open(output_file, "a") as f:
                f.write(f"{server}\t{external_ip}\t{result}\n")
        
        except Exception as e:
            print(f"Fehler beim Test für {server}: {e}")
        
        finally:
            disconnect_vpn()
            # Kurze Pause vor dem nächsten Test
            time.sleep(2)
    
    print(f"\nTest abgeschlossen. Ergebnisse wurden in '{output_file}' gespeichert.")

if __name__ == "__main__":
    main()

