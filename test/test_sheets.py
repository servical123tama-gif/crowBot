"""
Test Google Sheets Connection
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

print("🔍 Testing Google Sheets Connection...")
print("=" * 60)

# 1. Check credentials.json
print("\n1️⃣  Checking credentials.json...")
if not os.path.exists('credentials.json'):
    print("   ❌ credentials.json NOT FOUND!")
    exit(1)

with open('credentials.json', 'r') as f:
    creds = json.load(f)

client_email = creds.get('client_email', 'NOT FOUND')
print(f"   ✅ Service Account Email: {client_email}")

# 2. Check .env
print("\n2️⃣  Checking .env configuration...")
sheet_id = os.getenv('GOOGLE_SHEET_ID', '')

if not sheet_id:
    print("   ❌ GOOGLE_SHEET_ID is empty in .env!")
    exit(1)

print(f"   ✅ Sheet ID: {sheet_id}")

# 3. Build Sheet URL
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
print(f"\n3️⃣  Your Google Sheet URL:")
print(f"   {sheet_url}")

# 4. Try to connect
print("\n4️⃣  Attempting to connect to Google Sheets...")
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json', scope
    )
    
    client = gspread.authorize(creds)
    print("   ✅ Authentication successful!")
    
    # Try to open sheet
    print(f"\n5️⃣  Opening sheet: {sheet_id}...")
    sheet = client.open_by_key(sheet_id)
    print(f"   ✅ Sheet opened: '{sheet.title}'")
    
    # List worksheets
    print(f"\n6️⃣  Available worksheets:")
    worksheets = sheet.worksheets()
    for ws in worksheets:
        print(f"   - {ws.title} ({ws.row_count} rows x {ws.col_count} cols)")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED! Connection is working!")
    print("\n💡 You can now run: python run.py")
    
except gspread.exceptions.SpreadsheetNotFound:
    print("   ❌ SHEET NOT FOUND (404 Error)")
    print("\n🔧 Possible solutions:")
    print("   1. Check if GOOGLE_SHEET_ID is correct in .env")
    print("   2. Make sure the sheet exists")
    print("   3. Share the sheet with service account email:")
    print(f"      → {client_email}")
    print("\n📋 How to share:")
    print("   1. Open your Google Sheet")
    print("   2. Click 'Share' button (top right)")
    print("   3. Add this email as Editor:")
    print(f"      {client_email}")
    print("   4. Uncheck 'Notify people'")
    print("   5. Click 'Share'")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    print(f"\n💡 Error type: {type(e).__name__}")