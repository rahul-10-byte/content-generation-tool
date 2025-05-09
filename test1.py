import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Retell vs Shopify Matcher", layout="wide")
st.title("📞 Retell AI Calls vs Shopify Orders Match")

st.markdown("Enter your API keys and date range to compare Retell calls with Shopify orders.")

# Example placeholders
st.caption("Example Retell API URL: https://api.retellai.com/v1/calls")
st.caption("Example Shopify Orders API URL: https://your-store.myshopify.com/admin/api/2023-04/orders.json?status=any")

# User inputs
retell_api_url = st.text_input("Retell AI API Endpoint", value="https://api.retellai.com/v2/list-calls")
shopify_api_url = st.text_input("Shopify Orders API Endpoint")

retell_api_key = st.text_input("Retell API Key", type="password")
shopify_api_key = st.text_input("Shopify API Key", type="password")
shopify_password = st.text_input("Shopify API Password", type="password")

# Date range filter
today = datetime.today()
def_date = (today - timedelta(days=7), today)
date_range = st.date_input("Select Date Range (based on call/order creation)", value=def_date)

# Comparison functions
def extract_shopify_contacts(orders):
    emails = set()
    phones = set()
    for order in orders:
        created_at = order.get("created_at")
        if created_at and not date_in_range(created_at):
            continue
        email = order.get("email") or order.get("contact_email")
        if email:
            emails.add(email.lower())
        phone = order.get("phone")
        if phone:
            phones.add(phone.replace(" ", "").replace("-", "").lower())
        customer = order.get("customer", {})
        if customer:
            if customer.get("email"):
                emails.add(customer["email"].lower())
            if customer.get("phone"):
                phones.add(customer["phone"].replace(" ", "").replace("-", "").lower())
    return {"emails": emails, "phones": phones}

def extract_retell_contacts(calls):
    contacts = []
    for call in calls:
        start_timestamp = call.get("start_timestamp")
        if start_timestamp and not timestamp_in_range(start_timestamp):
            continue
        email = call.get("retell_llm_dynamic_variables", {}).get("email")
        phone = call.get("to_number")
        contacts.append({
            "call_id": call.get("call_id"),
            "email": email.lower() if email else None,
            "phone": phone.replace(" ", "").replace("-", "").lower() if phone else None
        })
    return contacts

def compare_contacts(retell_contacts, shopify_contacts_raw):
    matched_results = []
    for order in shopify_contacts_raw:
        email = (order.get("email") or order.get("contact_email") or "").lower()
        phone = (order.get("phone") or order.get("customer", {}).get("phone") or "").replace(" ", "").replace("-", "").lower()

        for call in retell_contacts:
            if (call["email"] and call["email"] == email) or (call["phone"] and call["phone"] == phone):
                matched_results.append({
                    "call_id": call["call_id"],
                    "call_email": call["email"],
                    "call_phone": call["phone"],
                    "order_id": order.get("name"),
                    "order_email": email,
                    "order_phone": phone,
                    "customer_name": order.get("customer", {}).get("first_name", "") + " " + order.get("customer", {}).get("last_name", "")
                })
    return matched_results

def date_in_range(iso_date):
    if not iso_date:
        return False
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return date_range[0] <= dt.date() <= date_range[1]
    except:
        return False

def timestamp_in_range(ms_timestamp):
    dt = datetime.utcfromtimestamp(ms_timestamp / 1000)
    return date_range[0] <= dt.date() <= date_range[1]

# Fetch and compare
if st.button("🔍 Compare Calls with Orders"):
    if not (retell_api_url and shopify_api_url and retell_api_key and shopify_api_key and shopify_password):
        st.error("Please fill in all fields.")
    else:
        with st.spinner("Fetching data from APIs..."):
            try:
                # Retell API call using POST
                headers_retell = {
                    "Authorization": f"Bearer {retell_api_key}",
                    "Content-Type": "application/json"
                }
                retell_response = requests.post(retell_api_url, headers=headers_retell, json={})
                retell_response.raise_for_status()
                retell_data_raw = retell_response.json()
                retell_data = retell_data_raw if isinstance(retell_data_raw, list) else retell_data_raw.get("calls", [])

                # Shopify API call
                auth = (shopify_api_key, shopify_password)
                shopify_response = requests.get(shopify_api_url, auth=auth)
                shopify_response.raise_for_status()
                shopify_data = shopify_response.json()

                shopify_contacts = extract_shopify_contacts(shopify_data.get("orders", []))
                retell_contacts = extract_retell_contacts(retell_data)
                comparison_result = compare_contacts(retell_contacts, shopify_data.get("orders", []))

                df = pd.DataFrame(comparison_result)

                if df.empty:
                    st.warning("No matching data found. Double-check your API responses or date filter.")
                else:
                    st.subheader("🔍 Match Results")
                st.dataframe(df[df["order_id"].notnull()], use_container_width=True)

                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", data=csv, file_name="retell_vs_shopify_matches.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Failed to fetch or process data: {e}")
