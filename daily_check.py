import os
import json
import requests
from datetime import datetime
from monitor import fetch_federal_register_updates, check_page_snapshot, send_role_based_alert

SEED_FILE = "seed_data.json"

def run_daily_checks():
    now_utc = datetime.utcnow()
    run_timestamp = now_utc.strftime("%A, %B %d, %Y at %I:%M %p UTC")
    run_date_str = now_utc.strftime("%Y-%m-%d")
    
    print(f"Starting daily policy run: {run_timestamp}")
    
    with open(SEED_FILE, "r") as f:
        data = json.load(f)
    
    # 1. Check Federal Register for MNT & Telehealth rules published today
    for term, role, policy_name in [
        ("Medical Nutrition Therapy", "Revenue Cycle", "Medical Nutrition Therapy (MNT) Act (H.R. 6199 / S. 3934)"),
        ("Physician Fee Schedule Telehealth", "Compliance", "Medicare Telehealth Policy (CAA 2026 / H.R. 7148)")
    ]:
        docs = fetch_federal_register_updates(term)
        for doc in docs:
            if doc.get("publication_date") == run_date_str:
                msg = f"New Federal Register Publication: {doc['title']} ({doc['html_url']})"
                print(f"[ALERT] {msg}")
                send_role_based_alert(role, policy_name, "New Federal Register Document Detected", msg)

    # 2. Check Compact Page Hash
    compact_check = check_page_snapshot("https://dietitianscompact.org/")
    if compact_check.get("success"):
        print(f"Dietitians Compact snapshot verified (Hash: {compact_check['hash'][:10]}...)")

    # 3. Update metadata and last_checked dates
    for pol in data["policies"]:
        pol["last_checked"] = run_date_str

    data["system_metadata"] = {
        "last_automated_update": run_timestamp,
        "last_update_date": run_date_str,
        "status": "Active & Monitored"
    }
    
    with open(SEED_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Daily monitor successfully recorded for {run_timestamp}.")

if __name__ == "__main__":
    run_daily_checks()
