#!/usr/bin/env python3
import subprocess
import time
import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_london_instances():
    """
    Ruft über die Cyberghost-CLI die Liste der Server für London ab.
    Es wird erwartet, dass der City-Name "London" in der Ausgabe vorkommt.
    Liefert als Liste die Serverinstanzen, z. B. "london-s315-i01".
    """
    # Wir verwenden hier den City-Namen "London"
    result = subprocess.run(["cyberghostvpn", "--country-code", "gb", "--city", "london"],
                            capture_output=True, text=True)
    output = result.stdout
    instances = []
    for line in output.splitlines():
        if line.startswith("|"):
            parts = line.split("|")
            if len(parts) >= 4:
                instance = parts[3].strip()
                # Erwartetes Format: "london-s315-i01"
                if re.match(r".*-s\d+-i\d+", instance) or instance.isdigit():
                    instances.append(instance)
    return instances

def connect_vpn(city, instance):
    """
    Baut die VPN-Verbindung zum angegebenen Cyberghost-Server auf.
    Es muss dabei der Country-Code (gb), der City-Name und der Server angegeben werden.
    """
    print(f"Verbinde mit {instance} in {city} ...")
    subprocess.run(["sudo", "cyberghostvpn", "--country-code", "gb", "--city", city.lower(), "--server", instance, "--connect"],
                   capture_output=True, text=True)
    # Warten, damit sich die Verbindung stabilisieren kann
    time.sleep(15)

def disconnect_vpn():
    """
    Trennt die VPN-Verbindung.
    """
    subprocess.run(["sudo", "cyberghostvpn", "--disconnect"],
                   capture_output=True, text=True)
    print("VPN-Verbindung getrennt.")
    time.sleep(8)

def check_external_ip():
    """
    Fragt per curl die aktuelle externe IP-Adresse ab (mittels ip.me).
    """
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
    time.sleep(6)  # Warte, bis die Seite vollständig geladen ist
    
    page_source = driver.page_source
    driver.quit()
    if "Sorry, BBC iPlayer isn’t available in your region." in page_source:
        return "Blocked"
    else:
        return "Available"

def main():
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    # Standard-Dateinamen für London-Serverliste und Ergebnisse
    default_server_file = f"Cyberghost_London_{today}.txt"
    default_results_file = f"BBCiPlayer_Results_Cyberghost_London_{today}.txt"
    
    # Serverliste abrufen und speichern (nur London)
    print("Hole die London-Serverliste von Cyberghost ...")
    instances = get_london_instances()
    if not instances:
        print("Keine London-Server gefunden.")
        return
    with open(default_server_file, "w") as f:
        for inst in instances:
            f.write(f"{inst}\n")
    print(f"Serverliste wurde in '{default_server_file}' gespeichert.")
    
    # Ergebnisse-Datei initialisieren: drei Spalten: Instance, Externe IP, Ergebnis
    with open(default_results_file, "w") as f:
        f.write("Instance\tExterne IP\tErgebnis\n")
    
    # Teste jeden London-Server
    city = "London"
    for instance in instances:
        try:
            print(f"\nStarte Test für {instance} in {city} ...")
            connect_vpn(city, instance)
            time.sleep(5)
            external_ip = check_external_ip()
            print(f"Externe IP: {external_ip}")
            result = check_bbc_iplayer()
            print(f"{instance}\t{external_ip}\t{result}")
            with open(default_results_file, "a") as f:
                f.write(f"{instance}\t{external_ip}\t{result}\n")
        except Exception as e:
            print(f"Fehler beim Test für {instance} in {city}: {e}")
        finally:
            disconnect_vpn()
            time.sleep(2)
    
    print(f"\nTest abgeschlossen. Ergebnisse wurden in '{default_results_file}' gespeichert.")

if __name__ == "__main__":
    main()

