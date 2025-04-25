#!/usr/bin/env python3
import subprocess
import time
import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_uk_cities():
    """
    Ruft über die Cyberghost-CLI die Liste der UK-Städte ab.
    Erwartet wird die Ausgabe einer Tabelle, z. B.:
    
      +-----+------------+----------+------+
      | No. |    City    | Instance | Load |
      +-----+------------+----------+------+
      |  1  | Berkshire  |    81    | 37%  |
      |  2  | London     |   315    | 37%  |
      |  3  | Manchester |   185    | 38%  |
      +-----+------------+----------+------+
      
    Da hier nur der City-Name für den Verbindungsaufbau benötigt wird, sammeln wir diese.
    """
    result = subprocess.run(["cyberghostvpn", "--country-code", "gb"],
                            capture_output=True, text=True)
    output = result.stdout
    cities = set()
    for line in output.splitlines():
        if line.startswith("|"):
            parts = line.split("|")
            if len(parts) >= 3:
                city = parts[2].strip()
                if city.lower() != "city" and city:
                    cities.add(city)
    return sorted(cities)

def get_instances_for_city(city):
    """
    Ruft für eine bestimmte Stadt alle Server ab und extrahiert die Instance-Spalte.
    Erwartet wird eine Ausgabe ähnlich:
    
      +-----+------------+-----------------------+------+
      | No. |    City    |       Instance        | Load |
      +-----+------------+-----------------------+------+
      |  1  | London     | london-s315-i01       | 37%  |
      |  2  | London     | london-s315-i02       | 35%  |
      +-----+------------+-----------------------+------+
      
    Sollte die Ausgabe abweichen (z. B. nur Zahlen in der Instance-Spalte enthalten), 
    muss das Parsing ggf. angepasst werden.
    """
    result = subprocess.run(["cyberghostvpn", "--country-code", "gb", "--city", city.lower()],
                            capture_output=True, text=True)
    output = result.stdout
    instances = []
    for line in output.splitlines():
        if line.startswith("|"):
            parts = line.split("|")
            if len(parts) >= 4:
                instance = parts[3].strip()
                # Beispielhafter Check: Erwartet wird ein Format wie "london-s315-i01"
                # Falls nur Zahlen geliefert werden, nehme sie als solche.
                if re.match(r".*-s\d+-i\d+", instance) or instance.isdigit():
                    instances.append(instance)
    return instances

def connect_vpn(city, instance):
    """
    Baut die VPN-Verbindung zu dem übergebenen Cyberghost-Server auf.
    Es muss dabei der Country-Code (gb), die Stadt und der Server angegeben werden.
    """
    print(f"Verbinde mit {instance} in {city} ...")
    subprocess.run(["sudo", "cyberghostvpn", "--country-code", "gb", "--city", city.lower(), "--server", instance, "--connect"],
                   capture_output=True, text=True)
    # Warten, damit sich die Verbindung stabilisieren kann
    time.sleep(10)

def disconnect_vpn():
    """
    Trennt die VPN-Verbindung.
    """
    subprocess.run(["sudo", "cyberghostvpn", "--disconnect"],
                   capture_output=True, text=True)
    print("VPN-Verbindung getrennt.")
    time.sleep(6)

def check_external_ip():
    """
    Fragt per curl die aktuelle externe IP-Adresse ab (mittels ip.me).
    """
    result = subprocess.run(["curl", "-s", "ip.me"], capture_output=True, text=True)
    return result.stdout.strip()

def check_bbc_iplayer():
    """
    Startet einen Headless Chrome (via Selenium) und lädt die BBC iPlayer-Seite.
    Wird in der Seitenquelle der Blockierungshinweis gefunden, gilt der Test als "Blocked".
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)
    
    url = "https://www.bbc.co.uk/iplayer"
    driver.get(url)
    time.sleep(6)  # Warte, bis die Seite vollständig geladen ist
    
    page_source = driver.page_source
    driver.quit()
    if "Sorry, BBC iPlayer isn’t available in your region." in page_source:
        return "Blocked"
    else:
        return "Available"

def main():
    # Heutiges Datum im Format YYYYMMDD
    today = datetime.datetime.now().strftime("%Y%m%d")
    server_filename = f"Cyberghost_GB_{today}.txt"
    result_filename = f"BBCiPlayer_Results_Cyberghost_GB_{today}.txt"
    
    # Dateinamen abfragen
    input_file = input(f"Bitte Dateinamen für die Serverliste eingeben (Standard: {server_filename}): ").strip()
    if not input_file:
        input_file = server_filename

    print("Hole die UK-Serverliste von Cyberghost ...")
    cities = get_uk_cities()
    all_instances = {}
    for city in cities:
        print(f"Verarbeite Stadt: {city}")
        instances = get_instances_for_city(city)
        all_instances[city] = instances

    # Speichern der Serverliste
    with open(input_file, "w") as f:
        for city, instances in all_instances.items():
            f.write(f"{city}:\n")
            for inst in instances:
                f.write(f"  {inst}\n")
    print(f"Serverliste wurde in '{input_file}' gespeichert.")
    
    # Ergebnisse-Dateinamen abfragen
    output_file = input(f"Bitte Dateinamen für die Ergebnisse eingeben (Standard: {result_filename}): ").strip()
    if not output_file:
        output_file = result_filename
    # Ergebnisse-Datei initialisieren: drei Spalten: Instance, Externe IP, Ergebnis
    with open(output_file, "w") as f:
        f.write("Instance\tExterne IP\tErgebnis\n")
    
    # Iteriere über alle Server und teste BBC iPlayer
    for city, instances in all_instances.items():
        for instance in instances:
            try:
                print(f"\nStarte Test für {instance} in {city} ...")
                connect_vpn(city, instance)
                # Warte, damit sich die VPN-Verbindung aufbauen kann
                time.sleep(10)
                # Externe IP abfragen
                external_ip = check_external_ip()
                print(f"Externe IP: {external_ip}")
                # BBC iPlayer testen
                result = check_bbc_iplayer()
                print(f"{instance}\t{external_ip}\t{result}")
                # Ergebnis in die Ergebnisdatei schreiben
                with open(output_file, "a") as f:
                    f.write(f"{instance}\t{external_ip}\t{result}\n")
            except Exception as e:
                print(f"Fehler beim Test für {instance} in {city}: {e}")
            finally:
                disconnect_vpn()
                # Kurze Pause vor dem nächsten Test
                time.sleep(5)
    
    print(f"\nTest abgeschlossen. Ergebnisse wurden in '{output_file}' gespeichert.")

if __name__ == "__main__":
    main()

