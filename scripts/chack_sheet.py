"""
Check which Google Sheet is being accessed
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

sheet_id = os.getenv('GOOGLE_SHEET_ID', '')

print("=" * 70)
print("🔍 CHECKING GOOGLE SHEET")
print("=" * 70)

print(f"\n📋 Sheet ID from .env:")
print(f"   {sheet_id}")

print(f"\n🔗 Expected URL:")
expected_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
print(f"   {expected_url}")

print(f"\n3️⃣  Connecting to Google Sheets...")

try:
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json', scope
    )
    client = gspread.authorize(creds)
    
    sheet = client.open_by_key(sheet_id)
    
    print(f"   ✅ Connected to sheet: '{sheet.title}'")
    print(f"\n📊 Current worksheets:")
    
    worksheets = sheet.worksheets()
    for idx, ws in enumerate(worksheets, 1):
        print(f"   {idx}. {ws.title}")
        
        # Show first row (headers)
        try:
            headers = ws.row_values(1)
            if headers:
                print(f"      Headers: {headers}")
            else:
                print(f"      (empty)")
        except:
            print(f"      (no data)")
    
    print(f"\n💡 Open this URL in your browser:")
    print(f"   {expected_url}")
    print(f"\n⚠️  Make sure this is the SAME sheet you're looking at!")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 70)