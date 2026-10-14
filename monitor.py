import os
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup

FEDERAL_REGISTER_API = "https://www.federalregister.gov/api/v1/documents.json"

def fetch_federal_register_updates(search_term="Medical Nutrition Therapy"):
    """Queries the live, public Federal Register API for CMS rules & notices."""
    params = {
        "conditions[term]": search_term,
        "conditions[agencies][]": "centers-for-medicare-medicaid-services",
        "per_page": 5,
        "order": "newest"
    }
    try:
        response = requests.get(FEDERAL_REGISTER_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = []
        for doc in data.get("results", []):
            results.append({
                "title": doc.get("title"),
                "type": doc.get("type"),
                "publication_date": doc.get("publication_date"),
                "html_url": doc.get("html_url"),
                "abstract": doc.get("abstract") or "No abstract provided."
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]

def check_page_snapshot(url):
    """Fetches a webpage, strips boilerplate, and returns text + SHA256 hash for the audit trail."""
    try:
        headers = {"User-Agent": "RD-Telehealth-Policy-Monitor/1.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        clean_text = " ".join(soup.stripped_strings)[:3000]
        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        return {
            "success": True,
            "hash": content_hash,
            "snippet": clean_text[:600] + "...",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_role_based_alert(role, policy_name, summary, so_what):
    """Routes policy alerts to role-specific Slack webhooks (Compliance, RevCycle, BD)."""
    webhook_map = {
        "Compliance": os.getenv("SLACK_WEBHOOK_COMPLIANCE"),
        "Revenue Cycle": os.getenv("SLACK_WEBHOOK_REVCYCLE"),
        "Business Development": os.getenv("SLACK_WEBHOOK_BD")
    }
    webhook_url = webhook_map.get(role)
    payload = {
        "text": (
            f"🚨 *Policy Alert for {role}* 🚨\n"
            f"*Policy:* {policy_name}\n"
            f"*Change Summary:* {summary}\n"
            f"*Business Impact ('So What'):* {so_what}"
        )
    }
    if not webhook_url:
        return False, f"Simulated alert to [{role}] (Set SLACK_WEBHOOK in .env for live Slack delivery)"
    try:
        r = requests.post(webhook_url, json=payload, timeout=5)
        return r.status_code == 200, "Delivered to Slack"
    except Exception as e:
        return False, str(e)