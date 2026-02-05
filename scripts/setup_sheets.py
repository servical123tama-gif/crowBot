"""
Auto Setup Google Sheets Structure
"""
import sys
import os

# Tambahkan parent directory ke Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app.config.settings import settings
from app.config.constants import *

def setup_sheets():
    """Setup Google Sheets with proper structure"""
    print("=" * 70)
    print(settings.BOT_NAME)
    print("🔧 SETTING UP GOOGLE SHEETS")
    print("=" * 70)
    
    try:
        # Validate settings
        print("\n1️⃣  Validating configuration...")
        if not settings.GOOGLE_SHEET_ID:
            print("   ❌ GOOGLE_SHEET_ID is empty in .env")
            return False
        
        if not os.path.exists(settings.CREDENTIALS_FILE):
            print(f"   ❌ {settings.CREDENTIALS_FILE} not found")
            return False
        
        print(f"   ✅ Sheet ID: {settings.GOOGLE_SHEET_ID}")
        print(f"   ✅ Credentials: {settings.CREDENTIALS_FILE}")
        
        # Connect to Google Sheets
        print("\n2️⃣  Connecting to Google Sheets...")
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            settings.CREDENTIALS_FILE, scope
        )
        client = gspread.authorize(creds)
        
        print("   ✅ Authentication successful")
        
        # Open sheet
        print(f"\n3️⃣  Opening spreadsheet...")
        sheet = client.open_by_key(settings.GOOGLE_SHEET_ID)
        print(f"   ✅ Opened: '{sheet.title}'")
        
        # Setup Transactions sheet
        print(f"\n4️⃣  Setting up '{SHEET_TRANSACTIONS}' sheet...")
        try:
            transactions_sheet = sheet.worksheet(SHEET_TRANSACTIONS)
            print(f"   ℹ️  Sheet already exists")
            
            # Check if headers exist
            try:
                headers = transactions_sheet.row_values(1)
                if headers == ['Date', 'Capster', 'Service','Price', 'Payment_Method','Branch']:
                    print(f"   ✅ Headers already correct")
                else:
                    print(f"   ⚠️  Updating headers...")
                    transactions_sheet.update('A1:F1', [['Date', 'Capster', 'Service','Price', 'Payment_Method','Branch']])
                    print(f"   ✅ Headers updated")
            except:
                print(f"   ⚠️  Adding headers...")
                transactions_sheet.update('A1:F1', [['Date', 'Capster', 'Service','Price', 'Payment_Method','Branch']])
                print(f"   ✅ Headers added")
                
        except gspread.exceptions.WorksheetNotFound:
            print(f"   📝 Creating new sheet...")
            transactions_sheet = sheet.add_worksheet(
                title=SHEET_TRANSACTIONS,
                rows=1000,
                cols=10
            )
            # Add headers
            transactions_sheet.update('A1:F1', [['Date', 'Capster', 'Service','Price', 'Payment_Method','Branch']])
            print(f"   ✅ Sheet created with headers")
        
        # Setup Capsters sheet
        print(f"\n5️⃣  Setting up '{SHEET_CAPSTERS}' sheet...")
        try:
            capsters_sheet = sheet.worksheet(SHEET_CAPSTERS)
            print(f"   ℹ️  Sheet already exists")
            
            try:
                headers = capsters_sheet.row_values(1)
                if headers == ['Name', 'Telegram_ID', 'Status', 'Join_Date']:
                    print(f"   ✅ Headers already correct")
                else:
                    print(f"   ⚠️  Updating headers...")
                    capsters_sheet.update('A1:D1', [['Name', 'Telegram_ID', 'Status', 'Join_Date']])
                    print(f"   ✅ Headers updated")
            except:
                print(f"   ⚠️  Adding headers...")
                capsters_sheet.update('A1:D1', [['Name', 'Telegram_ID', 'Status', 'Join_Date']])
                print(f"   ✅ Headers added")
                
        except gspread.exceptions.WorksheetNotFound:
            print(f"   📝 Creating new sheet...")
            capsters_sheet = sheet.add_worksheet(
                title=SHEET_CAPSTERS,
                rows=100,
                cols=5
            )
            capsters_sheet.update('A1:D1', [['Name', 'Telegram_ID', 'Status', 'Join_Date']])
            print(f"   ✅ Sheet created with headers")
        
        # Setup Summary sheet
        print(f"\n6️⃣  Setting up '{SHEET_SUMMARY}' sheet...")
        try:
            summary_sheet = sheet.worksheet(SHEET_SUMMARY)
            print(f"   ℹ️  Sheet already exists")
            
            try:
                headers = summary_sheet.row_values(1)
                expected = ['Period', 'Type', 'Total_Transactions', 'Total_Revenue', 'Generated_Date']
                if headers == expected:
                    print(f"   ✅ Headers already correct")
                else:
                    print(f"   ⚠️  Updating headers...")
                    summary_sheet.update('A1:E1', [expected])
                    print(f"   ✅ Headers updated")
            except:
                print(f"   ⚠️  Adding headers...")
                summary_sheet.update('A1:E1', [['Period', 'Type', 'Total_Transactions', 'Total_Revenue', 'Generated_Date']])
                print(f"   ✅ Headers added")
                
        except gspread.exceptions.WorksheetNotFound:
            print(f"   📝 Creating new sheet...")
            summary_sheet = sheet.add_worksheet(
                title=SHEET_SUMMARY,
                rows=100,
                cols=10
            )
            summary_sheet.update('A1:E1', [['Period', 'Type', 'Total_Transactions', 'Total_Revenue', 'Generated_Date']])
            print(f"   ✅ Sheet created with headers")

        # Setup Customers sheet
        print(f"\n7️⃣  Setting up '{SHEET_CUSTOMERS}' sheet...")
        try:
            customers_sheet = sheet.worksheet(SHEET_CUSTOMERS)
            print(f"   ℹ️  Sheet already exists")
            
            try:
                headers = customers_sheet.row_values(1)
                if headers == ['Name', 'Phone']:
                    print(f"   ✅ Headers already correct")
                else:
                    print(f"   ⚠️  Updating headers...")
                    customers_sheet.update('A1:B1', [['Name', 'Phone']])
                    print(f"   ✅ Headers updated")
            except:
                print(f"   ⚠️  Adding headers...")
                customers_sheet.update('A1:B1', [['Name', 'Phone']])
                print(f"   ✅ Headers added")
                
        except gspread.exceptions.WorksheetNotFound:
            print(f"   📝 Creating new sheet...")
            customers_sheet = sheet.add_worksheet(
                title=SHEET_CUSTOMERS,
                rows=1000,
                cols=5
            )
            customers_sheet.update('A1:B1', [['Name', 'Phone']])
            print(f"   ✅ Sheet created with headers")
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ GOOGLE SHEETS SETUP COMPLETED!")
        print("=" * 70)
        print(f"\n📊 Sheet Details:")
        print(f"   Sheet ID: {settings.GOOGLE_SHEET_ID}")
        print(f"   Sheet Name: {sheet.title}")
        print(f"   URL: https://docs.google.com/spreadsheets/d/{settings.GOOGLE_SHEET_ID}")
        print(f"\n📋 Worksheets created:")
        print(f"   1. {SHEET_TRANSACTIONS} (Date, Capster, Service, Price)")
        print(f"   2. {SHEET_CAPSTERS} (Name, Telegram_ID, Status, Join_Date)")
        print(f"   3. {SHEET_SUMMARY} (Period, Type, Total_Transactions, Total_Revenue, Generated_Date)")
        print(f"   4. {SHEET_CUSTOMERS} (Name, Phone)")
        print("\n💡 Your bot is now ready to save transactions!")
        print("=" * 70)
        
        return True
        
    except gspread.exceptions.SpreadsheetNotFound:
        print("\n" + "=" * 70)
        print("❌ ERROR: Spreadsheet not found (404)")
        print("=" * 70)
        print("\n🔧 Possible solutions:")
        print("   1. Check if GOOGLE_SHEET_ID in .env is correct")
        print("   2. Make sure the Google Sheet exists")
        print("   3. Share the sheet with service account:")
        
        # Read service account email
        try:
            import json
            with open(settings.CREDENTIALS_FILE) as f:
                creds_data = json.load(f)
            print(f"      → {creds_data.get('client_email', 'N/A')}")
        except:
            print("      → (check credentials.json)")
        
        print("\n📋 How to share:")
        print("   1. Open Google Sheets")
        print("   2. Click 'Share' button")
        print("   3. Add service account email as Editor")
        print("   4. Uncheck 'Notify people'")
        print("   5. Click 'Share'")
        print("=" * 70)
        return False
        
    except FileNotFoundError as e:
        print("\n" + "=" * 70)
        print(f"❌ ERROR: File not found")
        print("=" * 70)
        print(f"\n{e}")
        print("\n💡 Make sure credentials.json exists in project root")
        print("=" * 70)
        return False
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ ERROR: {e}")
        print("=" * 70)
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        print("=" * 70)
        return False

if __name__ == '__main__':
    success = setup_sheets()
    
    if not success:
        print("\n⚠️  Setup failed. Please fix the errors above.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    else:
        input("\nPress Enter to exit...")
        sys.exit(0)