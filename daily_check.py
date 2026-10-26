import os
import json
import requests
from datetime import datetime
from monitor import fetch_federal_register_updates, check_page_snapshot, send_role_based_alert

SEED_FILE = "seed_data.json"

def run_daily_checks():
    print(f"Starting daily policy run: {datetime.utcnow().isoformat()}Z")
    
    with open(SEED_FILE, "r") as f:
        data = json.load(f)
    
    updated = False
    
    # 1. Check Federal Register for MNT & Telehealth rules published today
    for term, role, policy_name in [
        ("Medical Nutrition Therapy", "Revenue Cycle", "Medical Nutrition Therapy (MNT) Act (H.R. 6199 / S. 3934)"),
        ("Physician Fee Schedule Telehealth", "Compliance", "Medicare Telehealth Policy (CAA 2026 / H.R. 7148)")
    ]:
        docs = fetch_federal_register_updates(term)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        for doc in docs:
            if doc.get("publication_date") == today_str:
                msg = f"New Federal Register Publication: {doc['title']} ({doc['html_url']})"
                print(f"[ALERT] {msg}")
                send_role_based_alert(role, policy_name, "New Federal Register Document Detected", msg)
                updated = True

    # 2. Check Compact Page Hash for Rulemaking Changes
    compact_check = check_page_snapshot("https://dietitianscompact.org/")
    if compact_check.get("success"):
        print(f"Dietitians Compact snapshot verified (Hash: {compact_check['hash'][:10]}...)")

    # 3. Update last_checked timestamp in seed_data.json
    for pol in data["policies"]:
        pol["last_checked"] = datetime.utcnow().strftime("%Y-%m-%d")
    
    with open(SEED_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print("seed_data.json updated successfully.")

if __name__ == "__main__":
    run_daily_checks()
