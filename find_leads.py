"""
Delhi NCR Professional Lead Finder
Usage: python find_leads.py "CA"
       python find_leads.py "mutual fund distributor"
       python find_leads.py "insurance agent"

Runs for 30 minutes, finds leads across Delhi NCR cities,
saves to Excel (one tab per city), and pushes to GitHub.
"""

import sys
import time
import os
import requests
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
from config import MAPS_API_KEY, GITHUB_TOKEN, GITHUB_REPO

# ─── CONFIG ───────────────────────────────────────────────────────────────────
RUN_MINUTES = 30
OUTPUT_DIR  = os.path.dirname(os.path.abspath(__file__))

NCR_CITIES = [
    "Gurugram",
    "Delhi",
    "Noida",
    "Faridabad",
    "Ghaziabad",
    "Greater Noida",
]

# ─── GOOGLE PLACES API (New) ──────────────────────────────────────────────────
NEW_SEARCH_URL  = "https://places.googleapis.com/v1/places:searchText"
NEW_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

SEARCH_FIELDS   = "places.id,places.displayName,places.nationalPhoneNumber,places.internationalPhoneNumber,places.websiteUri,places.formattedAddress,places.types"
DETAILS_FIELDS  = "id,displayName,nationalPhoneNumber,internationalPhoneNumber,websiteUri,formattedAddress,types"


def search_places(query, city):
    """Text search using the new Places API. Returns list of place dicts."""
    results      = []
    page_token   = None
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_API_KEY,
        "X-Goog-FieldMask": SEARCH_FIELDS,
    }

    while True:
        body = {
            "textQuery": f"{query} in {city}",
            "languageCode": "en",
            "maxResultCount": 20,
        }
        if page_token:
            body["pageToken"] = page_token

        resp = requests.post(NEW_SEARCH_URL, headers=headers, json=body, timeout=15)
        if resp.status_code != 200:
            print(f"  [Maps] {city}: HTTP {resp.status_code} - {resp.text[:200]}")
            break

        data  = resp.json()
        places = data.get("places", [])
        results.extend(places)

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(2)

    return results


def get_place_details(place_id):
    """Fetch full details for a place using the new Places API."""
    url     = NEW_DETAILS_URL.format(place_id=place_id)
    headers = {
        "X-Goog-Api-Key": MAPS_API_KEY,
        "X-Goog-FieldMask": DETAILS_FIELDS,
    }
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        return {}
    return resp.json()


# ─── EXCEL WRITER ─────────────────────────────────────────────────────────────
HEADER     = ["Name", "Phone", "International Phone", "Website", "Address", "City", "Type / Position", "Source", "Fetched At"]
HDR_FILL   = PatternFill("solid", start_color="1F3864")
HDR_FONT   = Font(bold=True, color="FFFFFF", size=11, name="Arial")
ALT_FILL   = PatternFill("solid", start_color="DCE6F1")
NORM_FILL  = PatternFill("solid", start_color="FFFFFF")
BORDER     = Border(
    left=Side(style="thin", color="B8CCE4"),
    right=Side(style="thin", color="B8CCE4"),
    top=Side(style="thin", color="B8CCE4"),
    bottom=Side(style="thin", color="B8CCE4"),
)
COL_WIDTHS = [35, 18, 20, 35, 45, 15, 25, 25, 20]


def style_sheet(ws):
    for ci, (title, width) in enumerate(zip(HEADER, COL_WIDTHS), start=1):
        cell = ws.cell(row=1, column=ci, value=title)
        cell.font      = HDR_FONT
        cell.fill      = HDR_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = BORDER
        ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = width
    ws.row_dimensions[1].height = 22
    ws.freeze_panes = "A2"


def append_row(ws, row_data, row_num):
    fill = ALT_FILL if row_num % 2 == 0 else NORM_FILL
    for ci, val in enumerate(row_data, start=1):
        cell           = ws.cell(row=row_num, column=ci, value=val)
        cell.font      = Font(name="Arial", size=10)
        cell.fill      = fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border    = BORDER


def infer_position(professional_type):
    pt = professional_type.lower()
    if "ca" in pt or "chartered" in pt:
        return "Chartered Accountant (CA)"
    if "mfd" in pt or "mutual fund" in pt:
        return "Mutual Fund Distributor (MFD)"
    if "insurance" in pt:
        return "Insurance Agent"
    if "financial" in pt or "finance" in pt:
        return "Financial Advisor"
    if "tax" in pt:
        return "Tax Consultant"
    if "stock" in pt or "broker" in pt:
        return "Stock Broker"
    return professional_type.title()


# ─── GITHUB PUSH ──────────────────────────────────────────────────────────────
def push_to_github(filepath, professional_type):
    import base64

    filename = os.path.basename(filepath)
    api_url  = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers  = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    with open(filepath, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    sha   = None
    check = requests.get(api_url, headers=headers, timeout=15)
    if check.status_code == 200:
        sha = check.json().get("sha")

    payload = {
        "message": f"Update {professional_type} leads - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(api_url, headers=headers, json=payload, timeout=30)
    if resp.status_code in (200, 201):
        print(f"  [GitHub] Pushed {filename}")
    else:
        print(f"  [GitHub] Push failed: {resp.status_code} - {resp.text[:200]}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def run(professional_type: str):
    deadline       = time.time() + RUN_MINUTES * 60
    timestamp      = datetime.now().strftime("%Y%m%d_%H%M")
    safe_name      = professional_type.replace(" ", "_").replace("/", "-")
    out_file       = os.path.join(OUTPUT_DIR, f"{safe_name}_{timestamp}.xlsx")
    position_label = infer_position(professional_type)

    print(f"\n{'='*60}")
    print(f"  Lead Finder : {professional_type.upper()}")
    print(f"  Cities      : {', '.join(NCR_CITIES)}")
    print(f"  Run time    : {RUN_MINUTES} minutes")
    print(f"  Output      : {os.path.basename(out_file)}")
    print(f"{'='*60}\n")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    city_sheets = {}
    city_rows   = {}
    city_seen   = {}
    total_found = 0

    for city in NCR_CITIES:
        ws = wb.create_sheet(city)
        style_sheet(ws)
        city_sheets[city] = ws
        city_rows[city]   = 2
        city_seen[city]   = set()

    for city in NCR_CITIES:
        if time.time() > deadline:
            print("  [Time] 30 minutes reached — stopping.")
            break

        print(f"\n[{city}] Searching '{professional_type}'...")
        places = search_places(professional_type, city)
        print(f"  Found {len(places)} results.")

        for place in places:
            if time.time() > deadline:
                break

            place_id = place.get("id", "")
            if not place_id:
                continue

            name    = place.get("displayName", {}).get("text", "")
            phone   = place.get("nationalPhoneNumber", "")
            intl    = place.get("internationalPhoneNumber", "")
            website = place.get("websiteUri", "")
            address = place.get("formattedAddress", "")

            # Skip if no phone at all
            if not phone and not intl:
                continue

            dedup_key = intl or phone
            if dedup_key in city_seen[city]:
                continue
            city_seen[city].add(dedup_key)

            row = [
                name,
                phone,
                intl,
                website,
                address,
                city,
                position_label,
                "Google Maps Business Profile",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ]
            append_row(city_sheets[city], row, city_rows[city])
            city_rows[city] += 1
            total_found     += 1
            print(f"  + {name} | {phone or intl}")
            time.sleep(0.1)

    wb.save(out_file)
    print(f"\n[Done] {total_found} leads -> {os.path.basename(out_file)}")
    print("\nCity breakdown:")
    for city in NCR_CITIES:
        print(f"  {city:20s}: {city_rows[city] - 2} leads")

    print("\n[GitHub] Pushing...")
    push_to_github(out_file, professional_type)
    return out_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python find_leads.py "CA"')
        print('       python find_leads.py "mutual fund distributor"')
        print('       python find_leads.py "insurance agent"')
        sys.exit(1)

    run(" ".join(sys.argv[1:]))
