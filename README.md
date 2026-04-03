# Delhi NCR Professional Lead Finder

Automatically finds CAs, Mutual Fund Distributors, Insurance Agents and other professionals across **Delhi NCR** using Google Maps Business Profile (real phone numbers only).

## Cities Covered
- Gurugram
- Delhi
- Noida
- Faridabad
- Ghaziabad
- Greater Noida

## How to Use

### Install dependencies (first time only)
```bash
pip install requests openpyxl
```

### Run
```bash
python find_leads.py "CA"
python find_leads.py "mutual fund distributor"
python find_leads.py "insurance agent"
python find_leads.py "financial advisor"
python find_leads.py "tax consultant"
```

## What it does
- Runs for **30 minutes** each session
- Searches Google Maps Business Profile (real, verified phone numbers)
- Skips any entry without a phone number
- Creates an **Excel file** with one tab per city
- **Auto-pushes** to this GitHub repo when done

## Output columns
| Column | Description |
|--------|-------------|
| Name | Business/professional name |
| Phone | Local format |
| International Phone | +91 format |
| Website / Email | Business website |
| Address | Full address |
| City | NCR city |
| Type / Position | CA / MFD / Insurance Agent etc. |
| Source | Google Maps Business Profile |
| Fetched At | Timestamp |

## Source reliability
Only Google Maps **Business Profile** listings with a verified phone number are included. No JustDial, Sulekha, or directories that hide numbers.
