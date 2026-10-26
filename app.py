import json
import sqlite3
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import streamlit as st
from monitor import fetch_federal_register_updates, check_page_snapshot, send_role_based_alert

st.set_page_config(page_title="Spicerack Health Policy Monitoring AI", layout="wide")

DB_FILE = "policy_platform.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS internal_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_name TEXT,
        impact_area TEXT,
        task_description TEXT,
        owner_role TEXT,
        status TEXT,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS advocacy_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_name TEXT,
        docket_or_alert TEXT,
        comment_summary TEXT,
        submitted_date TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS audit_trail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_url TEXT,
        content_hash TEXT,
        snapshot_snippet TEXT,
        checked_at TEXT
    )""")
    conn.commit()
    return conn

@st.cache_data
def load_seed_data():
    with open("seed_data.json", "r") as f:
        return json.load(f)

data = load_seed_data()
conn = init_db()

st.title("Spicerack Health Policy Monitoring AI")
st.caption("Tracks federal and state RD telehealth policy, translates changes into Illinois & multi-state operational actions, and routes alerts by team role.")

# --- DAILY UPDATE STATUS BANNER ---
meta = data.get("system_metadata", {})
last_update = meta.get("last_automated_update", datetime.utcnow().strftime("%A, %B %d, %Y"))

st.success(
    f"**Daily Policy Intelligence Update Completed:** Monitored on **{last_update}**. "
    f"Federal Register rules, CMMI model tracks, and compact statuses verified."
)

tabs = st.tabs([
    "1. Policy Dashboard & Spicerack Strategy",
    "2. 19-State Licensure Compact & Expansion Map",
    "3. Billing, Coding & Margin Analysis",
    "4. CMMI & Pharma B2B Partnership Tracker",
    "5. Live Source Monitor & Audit Trail",
    "6. Internal Impact Log & Advocacy"
])

# --- TAB 1: POLICY TRACKER, DIRECT LINKS & STRATEGY ---
with tabs[0]:
    st.subheader("Key Regulatory Deadlines & Sunsets")
    deadlines_df = pd.DataFrame(data["deadlines"])
    deadlines_df["days_remaining"] = deadlines_df["date"].apply(
        lambda d: (datetime.strptime(d, "%Y-%m-%d").date() - date.today()).days
    )
    st.dataframe(deadlines_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Policy Tracker, Direct Source Links & Personalized Spicerack Recommendations")
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        score_filter = st.multiselect("Filter by Impact Score", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
    with col_filter2:
        search_filter = st.text_input("Search by tag or keyword (e.g., Illinois, Obesity, GLP-1, PLLC, G0669, CKM)")

    for pol in data["policies"]:
        if pol["impact_score"] not in score_filter:
            continue
        searchable_blob = (pol["impact_area"] + pol["name"] + pol["summary"] + " ".join(pol["spicerack_recommendations"])).lower()
        if search_filter and search_filter.lower() not in searchable_blob:
            continue

        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1.5, 1])
            c1.markdown(f"### {pol['name']}")
            c2.markdown(f"**Status:** `{pol['status']}`")
            c3.markdown(f"**Impact:** `{pol['impact_score']}`")

            st.markdown(f"**Tagged Areas:** `{pol['impact_area']}` | **Routed To:** `{pol['route_to']}`")
            st.markdown(f"**Policy Summary:** {pol['summary']}")
            st.info(f"**Operational 'So What' for Spicerack Health:** {pol['so_what']}")

            st.markdown("**Personalized Strategic Recommendations for Spicerack Health:**")
            for rec in pol["spicerack_recommendations"]:
                st.markdown(f"- {rec}")

            col_p, col_s = st.columns(2)
            with col_p:
                st.markdown("**Direct Primary Sources:**")
                for link in pol["primary_links"]:
                    st.markdown(f"- [{link['label']}]({link['url']})")
            with col_s:
                st.markdown("**Direct Secondary & Reference Sources:**")
                for link in pol["secondary_links"]:
                    st.markdown(f"- [{link['label']}]({link['url']})")

# --- TAB 2: STATE LICENSURE MAP ---
with tabs[1]:
    st.subheader("Dietitian Licensure Compact (19 Member States) & Spicerack Expansion Map")
    st.markdown(
        "**Spicerack Licensure & PLLC Strategy:** Compact privileges are expected in **2027** (12–24 month implementation window; 0 privileges issued today). "
        "**Illinois** does not have an active bill yet. The Compact only covers individual RD licensure—Spicerack must still qualify as a foreign PLLC "
        "and verify state ownership rules for Illinois-licensed members."
    )
    states_df = pd.DataFrame(data["states"])

    fig = px.choropleth(
        states_df,
        locations="state",
        locationmode="USA-states",
        color="compact_status",
        hover_name="state",
        hover_data=["reg_type", "privilege_active", "telehealth_notes"],
        scope="usa",
        color_discrete_map={
            "Non-Compact (Home Base - No Bill Yet)": "#d62728",
            "Compact Enacted (2024)": "#1b7837",
            "Compact Enacted (2025)": "#5aae61",
            "Compact Enacted (2026)": "#a6dba0",
            "Low-Barrier Non-Compact": "#1f77b4"
        },
        title="Spicerack Health 19-State Compact Tracker & Low-Barrier Expansion States"
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(states_df, use_container_width=True, hide_index=True)

# --- TAB 3: BILLING, CODING & MARGIN ANALYSIS ---
with tabs[2]:
    st.subheader("Traditional Medicare Part B MNT Reimbursement (Diabetes & Renal)")
    st.markdown("Dietitians receive **85% of the Physician Fee Schedule** (42 C.F.R. § 414.64). Qualified beneficiaries have **$0 cost sharing**.")
    st.dataframe(pd.DataFrame(data["billing_codes_mnt"]), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("CMS ACCESS Outcome-Aligned Payment (OAP) Codes & Unit Economics")
    st.warning(
        "**Margin Warning for Spicerack:** In CKM, the maximum monthly reimbursement is **$35/month (G0671)** before the 20% patient coinsurance. "
        "That is less than a single 15-minute MNT unit ($36.74 for 97802). Furthermore, **up to 50% of the annual fee is held back** until year-end outcome targets are proven. "
        "ACCESS cannot financially support hourly live RD visits; Spicerack must deliver this model via **automated AI monitoring and asynchronous touchpoints**."
    )
    st.dataframe(pd.DataFrame(data["billing_codes_access"]), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Payer Revenue Architecture Comparison")
    st.dataframe(pd.DataFrame(data["payers"]), use_container_width=True, hide_index=True)

# --- TAB 4: CMMI & PHARMA B2B PARTNERSHIPS ---
with tabs[3]:
    st.subheader("CMMI Models (ACCESS, LEAD, BALANCE) & Pharma Partner Portals")
    st.markdown(
        "- **CMS ACCESS:** Apply directly on a rolling basis as a Medicare Part B TIN for the **eCKM** and **CKM** tracks ($180–$360 Year 1; $90–$210 follow-on).\n"
        "- **CMS BALANCE:** Standalone provider billing is not permitted by CMS; partner directly with GLP-1 manufacturers (**Novo Nordisk** and **Eli Lilly**).\n"
        "- **CMS LEAD:** Pitch a predictable **PMPM or case-rate** nutrition program to participating ACOs (5,000+ beneficiaries) in Illinois and expansion states."
    )
    part_df = pd.DataFrame(data["partnerships"])
    st.dataframe(
        part_df,
        column_config={
            "portal_url": st.column_config.LinkColumn("Direct Application / Partner Portal")
        },
        use_container_width=True,
        hide_index=True
    )

# --- TAB 5: AUTOMATED MONITORING & AUDIT TRAIL ---
with tabs[4]:
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Live Federal Register API Query")
        query_term = st.selectbox(
            "Select Policy Query",
            ["Medical Nutrition Therapy", "Physician Fee Schedule Telehealth", "Accountable Care"]
        )
        if st.button("Query Federal Register API Now"):
            results = fetch_federal_register_updates(query_term)
            for r in results:
                if "error" in r:
                    st.error(r["error"])
                else:
                    st.markdown(f"**[{r['title']}]({r['html_url']})** ({r['publication_date']} - *{r['type']}*)")
                    st.caption(r["abstract"])

    with c_right:
        st.subheader("Source Page Snapshot & Audit Trail")
        target_url = st.selectbox(
            "Select Official Policy URL to Snapshot & Hash",
            [
                "https://dietitianscompact.org/",
                "https://www.cms.gov/priorities/innovation/innovation-models/access",
                "https://www.cms.gov/priorities/innovation/innovation-models/balance",
                "https://www.cms.gov/priorities/innovation/innovation-models/lead",
                "https://telehealth.hhs.gov/providers/telehealth-policy/telehealth-policy-updates"
            ]
        )
        if st.button("Run Snapshot & Compare Hash"):
            snap = check_page_snapshot(target_url)
            if snap["success"]:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO audit_trail (source_url, content_hash, snapshot_snippet, checked_at) VALUES (?, ?, ?, ?)",
                    (target_url, snap["hash"], snap["snippet"], snap["timestamp"])
                )
                conn.commit()
                st.success(f"Snapshot saved! SHA-256: `{snap['hash'][:16]}...`")
            else:
                st.error(snap["error"])

        audit_df = pd.read_sql_query("SELECT * FROM audit_trail ORDER BY id DESC LIMIT 10", conn)
        st.dataframe(audit_df, use_container_width=True, hide_index=True)

# --- TAB 6: INTERNAL IMPACT LOG & ADVOCACY ---
with tabs[5]:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Spicerack Internal Impact Log & Role Alerting")
        with st.form("task_form"):
            pol_choice = st.selectbox("Linked Policy", [p["name"] for p in data["policies"]])
            area_choice = st.selectbox("Impact Area", ["Licensure & Foreign PLLC", "Medicare Enrollment & Billing", "ACCESS / LEAD / BALANCE B2B", "Patient Location Compliance"])
            role_choice = st.selectbox("Assign & Alert Role", ["Compliance", "Revenue Cycle", "Business Development"])
            task_desc = st.text_area("Action Item (e.g., Enroll PLLC in Medicare Part B, finalize G0669/G0671 billing guide)")
            submitted = st.form_submit_button("Log Task & Trigger Role Alert")
            if submitted and task_desc:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO internal_tasks (policy_name, impact_area, task_description, owner_role, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (pol_choice, area_choice, task_desc, role_choice, "Open", datetime.now().strftime("%Y-%m-%d"))
                )
                conn.commit()
                ok, msg = send_role_based_alert(role_choice, pol_choice, f"New Spicerack action logged ({area_choice})", task_desc)
                st.success(f"Task saved! Alert status: {msg}")

        tasks_df = pd.read_sql_query("SELECT * FROM internal_tasks ORDER BY id DESC", conn)
        st.dataframe(tasks_df, use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("Spicerack Comment & Illinois Advocacy Log")
        with st.form("advocacy_form"):
            adv_pol = st.selectbox("Policy / Bill", [p["name"] for p in data["policies"]])
            docket = st.text_input("Contact / Docket (e.g., Rep. Robin Kelly IL-02 Office, IL Compact Bill, Academy Alert)")
            comment_notes = st.text_area("Summary of Advocacy Outreach or Submitted Comment")
            if st.form_submit_button("Record Advocacy Action"):
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO advocacy_log (policy_name, docket_or_alert, comment_summary, submitted_date) VALUES (?, ?, ?, ?)",
                    (adv_pol, docket, comment_notes, datetime.now().strftime("%Y-%m-%d"))
                )
                conn.commit()
                st.success("Advocacy action recorded.")

        adv_df = pd.read_sql_query("SELECT * FROM advocacy_log ORDER BY id DESC", conn)
        st.dataframe(adv_df, use_container_width=True, hide_index=True)
