#!/usr/bin/env python3
import subprocess
import time
import datetime
import re

def get_cities():
    """
    Ruft über die Cyberghost-CLI die Liste der US-Städte ab.
    Erwartet wird die Ausgabe einer Tabelle (ähnlich wie bei `cyberghostvpn --country-code us`).
    """
    result = subprocess.run(["cyberghostvpn", "--country-code", "us"],
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
    Erwartet wird dabei eine Tabelle (z. B. von `cyberghostvpn --country-code us --city <city>`).
    """
    result = subprocess.run(["cyberghostvpn", "--country-code", "us", "--city", city.lower()],
                            capture_output=True, text=True)
    output = result.stdout
    instances = []
    for line in output.splitlines():
        if line.startswith("|"):
            parts = line.split("|")
            if len(parts) >= 4:
                instance = parts[3].strip()
                if re.match(r".*-s\d+-i\d+", instance):
                    instances.append(instance)
    return instances

def connect_vpn(city, instance):
    """
    Baut eine VPN-Verbindung zu dem übergebenen Cyberghost-Server auf.
    Hier wird der US-Country-Code, die Stadt und der Server angegeben.
    """
    print(f"Verbinde mit {instance} in {city} ...")
    subprocess.run(["sudo", "cyberghostvpn", "--country-code", "us", "--city", city.lower(), "--server", instance, "--connect"],
                   capture_output=True, text=True)
    # Warten, damit sich die Verbindung stabilisieren kann
    time.sleep(6)

def disconnect_vpn():
    """
    Trennt die VPN-Verbindung.
    """
    subprocess.run(["sudo", "cyberghostvpn", "--disconnect"],
                   capture_output=True, text=True)
    print("VPN-Verbindung getrennt.")
    time.sleep(4)

def check_external_ip():
    """
    Fragt per curl die aktuelle externe IP-Adresse ab (mittels ip.me).
    """
    result = subprocess.run(["curl", "-s", "ip.me"], capture_output=True, text=True)
    return result.stdout.strip()

def check_peacock():
    """
    Ruft mittels curl die finale URL von Peacock ab, um zu überprüfen, ob die Seite blockiert wird.
    """
    curl_proc = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{url_effective}", "-L", "https://www.peacocktv.com"],
        capture_output=True, text=True
    )
    return curl_proc.stdout.strip()

def main():
    # Heutiges Datum im Format YYYYMMDD
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    # Standard-Dateinamen für die Serverliste und die Ergebnisse
    default_server_file = f"Cyberghost_US_{today}.txt"
    default_results_file = f"Peacock_Results_Cyberghost_{today}.txt"
    
    # Frage nach dem Dateinamen für die Serverliste
    input_file = input(f"Bitte Dateinamen für die Serverliste eingeben (Standard: {default_server_file}): ").strip()
    if not input_file:
        input_file = default_server_file

    print("Hole die US-Serverliste von Cyberghost ...")
    cities = get_cities()
    all_instances = {}
    for city in cities:
        print(f"Verarbeite Stadt: {city}")
        instances = get_instances_for_city(city)
        all_instances[city] = instances

    # Speichern der Serverliste in der Datei
    with open(input_file, "w") as f:
        for city, instances in all_instances.items():
            f.write(f"{city}:\n")
            for inst in instances:
                f.write(f"  {inst}\n")
    print(f"Serverliste wurde in '{input_file}' gespeichert.")
    
    # Frage nach dem Dateinamen für die Ergebnisse
    output_file = input(f"Bitte Dateinamen für die Ergebnisse eingeben (Standard: {default_results_file}): ").strip()
    if not output_file:
        output_file = default_results_file
    
    # Ergebnisse-Datei initialisieren: nun mit drei Spalten: Instance, Externe IP, Ergebnis
    with open(output_file, "w") as f:
        f.write("Instance\tExterne IP\tErgebnis\n")
    
    # Iteriere über alle Server und teste Peacock
    for city, instances in all_instances.items():
        for instance in instances:
            print(f"\nStarte Test für {instance} in {city} ...")
            connect_vpn(city, instance)
            # Warte, damit sich die VPN-Verbindung aufbauen kann
            time.sleep(5)
            # Externe IP abfragen
            external_ip = check_external_ip()
            print(f"Externe IP: {external_ip}")
            # Peacock testen
            effective_url = check_peacock()
            if "/unavailable" in effective_url:
                result_text = "Blocked"
            else:
                result_text = "Available"
            print(f"{instance}\t{external_ip}\t{result_text}")
            # Ergebnis in die Ergebnisdatei schreiben
            with open(output_file, "a") as f:
                f.write(f"{instance}\t{external_ip}\t{result_text}\n")
            
            disconnect_vpn()
            # Kurze Pause vor dem nächsten Test
            time.sleep(2)
    
    print(f"\nTest abgeschlossen. Ergebnisse wurden in '{output_file}' gespeichert.")

if __name__ == "__main__":
    main()

