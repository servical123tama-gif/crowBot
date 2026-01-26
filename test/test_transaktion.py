"""
Test Transaction Save
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("🧪 TESTING TRANSACTION SAVE")
print("=" * 70)

# Test 1: Import modules
print("\n1️⃣  Testing imports...")
try:
    from app.services.sheets_service import SheetsService
    from app.models.transaction import Transaction
    print("   ✅ Imports successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Test 2: Create test transaction
print("\n2️⃣  Creating test transaction...")
try:
    transaction = Transaction(
        caster="Test User",
        service="✂️ Potong Rambut",
        price=35000,
        date=datetime.now()
    )
    print(f"   ✅ Transaction created: {transaction}")
except Exception as e:
    print(f"   ❌ Failed to create transaction: {e}")
    exit(1)

# Test 3: Initialize SheetsService
print("\n3️⃣  Initializing Google Sheets service...")
try:
    sheets = SheetsService()
    print("   ✅ SheetsService initialized")
except FileNotFoundError as e:
    print(f"   ❌ File not found: {e}")
    print("   💡 Make sure credentials.json exists")
    exit(1)
except Exception as e:
    print(f"   ❌ Failed to initialize: {e}")
    print(f"   Error type: {type(e).__name__}")
    exit(1)

# Test 4: Check if Transactions sheet exists
print("\n4️⃣  Checking 'Transactions' sheet...")
try:
    worksheet = sheets.sheet.worksheet('Transactions')
    print(f"   ✅ Sheet 'Transactions' found")
    print(f"   📊 Rows: {worksheet.row_count}, Cols: {worksheet.col_count}")
    
    # Check headers
    headers = worksheet.row_values(1)
    print(f"   📋 Headers: {headers}")
    
    expected_headers = ['Date', 'Caster', 'Service', 'Price']
    if headers != expected_headers:
        print(f"   ⚠️  Headers mismatch!")
        print(f"      Expected: {expected_headers}")
        print(f"      Found: {headers}")
        print("   💡 Run: python scripts/setup_sheets.py")
    
except Exception as e:
    print(f"   ❌ Sheet 'Transactions' not found: {e}")
    print("   💡 Run: python scripts/setup_sheets.py")
    exit(1)

# Test 5: Try to save transaction
print("\n5️⃣  Attempting to save transaction...")
try:
    result = sheets.add_transaction(transaction)
    
    if result:
        print("   ✅ Transaction saved successfully!")
        
        # Verify by reading back
        print("\n6️⃣  Verifying saved data...")
        all_records = worksheet.get_all_records()
        if all_records:
            last_record = all_records[-1]
            print(f"   📄 Last record in sheet:")
            print(f"      Date: {last_record.get('Date')}")
            print(f"      Caster: {last_record.get('Caster')}")
            print(f"      Service: {last_record.get('Service')}")
            print(f"      Price: {last_record.get('Price')}")
        else:
            print("   ⚠️  No records found in sheet")
    else:
        print("   ❌ Failed to save (returned False)")
        
except Exception as e:
    print(f"   ❌ Error saving transaction: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    print("\n   Full traceback:")
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ TEST COMPLETED")
print("=" * 70)