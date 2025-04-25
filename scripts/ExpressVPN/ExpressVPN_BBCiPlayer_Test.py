#!/usr/bin/env python3
import subprocess
import datetime
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def fetch_server_list():
    """
    Ruft die komplette Serverliste von ExpressVPN ab.
    Erwartet wird eine Ausgabe in Zeilen, z. B.:
      ukto  United Kingdom (GB)         UK - Tottenham                 Y
      ukel                             UK - East London               Y
      ukdo                             UK - Docklands                 Y
      uklo                             UK - London                    Y
    """
    result = subprocess.run(["expressvpn", "list", "all"], capture_output=True, text=True)
    return result.stdout

def parse_uk_server_list(output):
    """
    Parst die Ausgabe von "expressvpn list all" und filtert Zeilen, deren Location mit "UK -" beginnt.
    Liefert eine Liste von Dictionaries mit den Keys:
      - code: Server-Code (z.B. "ukto")
      - country: z.B. "United Kingdom (GB)" (kann auch leer sein)
      - location: z.B. "UK - London"
    """
    parsed = []
    lines = output.strip().splitlines()
    for line in lines:
        if not line.strip():
            continue
        # Spalten trennen – Annahme: mindestens zwei Leerzeichen als Trenner
        parts = re.split(r'\s{2,}', line)
        if len(parts) == 4:
            code, country, location, _ = parts
        elif len(parts) == 3:
            code, location, _ = parts
            country = ""
        else:
            continue  # Zeile entspricht nicht dem erwarteten Format
        # Nur UK-Server übernehmen, wenn die Location mit "UK -" beginnt
        if location.strip().startswith("UK -"):
            parsed.append({
                "code": code,
                "country": country,
                "location": location.strip()
            })
    return parsed

def save_server_list(parsed, filename):
    """Speichert die geparste Serverliste in eine Datei (Tab-getrennt)."""
    with open(filename, "w") as f:
        for server in parsed:
            f.write(f"{server['code']}\t{server['country']}\t{server['location']}\n")

def connect_vpn(location):
    """
    Baut die VPN-Verbindung zu dem angegebenen ExpressVPN-Server auf.
    Der Verbindungsbefehl lautet:
      expressvpn connect "<Location>"
    """
    print(f"Connecting to {location} ...")
    subprocess.run(["expressvpn", "connect", location], capture_output=True, text=True)
    # Warten, damit sich die Verbindung stabilisiert
    time.sleep(8)

def disconnect_vpn():
    """Trennt die VPN-Verbindung."""
    subprocess.run(["expressvpn", "disconnect"], capture_output=True, text=True)
    print("Disconnected VPN")
    time.sleep(3)

def check_external_ip():
    """Fragt per curl die externe IP ab (mittels curl ip.me)."""
    result = subprocess.run(["curl", "-s", "ip.me"], capture_output=True, text=True)
    return result.stdout.strip()

def check_bbc_iplayer():
    """
    Startet einen Headless-Chrome-Browser (via Selenium) und lädt die BBC iPlayer-Seite.
    Wird in der Seitenquelle der Blockierungshinweis gefunden, gilt der Test als "Blocked",
    andernfalls als "Available".
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
    server_filename = f"ExpressVPN_UK_{today}.txt"
    result_filename = f"BBCiPlayer_Results_ExpressVPN_UK_{today}.txt"
    
    # 1. Serverliste abrufen und filtern
    print("Hole die ExpressVPN-Serverliste ...")
    server_list_output = fetch_server_list()
    if not server_list_output:
        print("Fehler: Keine Serverliste erhalten.")
        return
    uk_servers = parse_uk_server_list(server_list_output)
    if not uk_servers:
        print("Keine UK-Server gefunden.")
        return
    save_server_list(uk_servers, server_filename)
    print(f"UK-Serverliste wurde in '{server_filename}' gespeichert.")
    
    # Ergebnisse-Datei initialisieren: vier Spalten: Location, Server Code, External IP, BBC iPlayer Ergebnis
    with open(result_filename, "w") as f:
        f.write("Location\tServer Code\tExternal IP\tBBC iPlayer Ergebnis\n")
    
    # 2. Für jeden UK-Server testen
    for server in uk_servers:
        location = server["location"]
        code = server["code"]
        print(f"\nStarte Test für {code} - {location}")
        
        connect_vpn(location)
        # Warte, damit sich die VPN-Verbindung sicher steht
        time.sleep(5)
        
        # Externe IP abfragen
        ext_ip = check_external_ip()
        print(f"Externe IP: {ext_ip}")
        
        # BBC iPlayer testen
        result = check_bbc_iplayer()
        print(f"{code}\t{ext_ip}\t{result}")
        
        # Ergebnis abspeichern
        with open(result_filename, "a") as f:
            f.write(f"{location}\t{code}\t{ext_ip}\t{result}\n")
        
        disconnect_vpn()
    
    print(f"\nTest abgeschlossen. Ergebnisse wurden in '{result_filename}' gespeichert.")

if __name__ == "__main__":
    main()

