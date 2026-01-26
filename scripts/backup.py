"""
Backup Script for Google Sheets Data
"""
import os
import sys
import json
from datetime import datetime

# Tambahkan parent directory ke Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.sheets_service import SheetsService

def backup_data():
    """Backup all transactions to JSON file"""
    print("=" * 70)
    print("💾 BACKUP GOOGLE SHEETS DATA")
    print("=" * 70)
    
    try:
        print("\n1️⃣  Connecting to Google Sheets...")
        sheets = SheetsService()
        print("   ✅ Connected")
        
        print("\n2️⃣  Fetching all transactions...")
        transactions = sheets.get_all_transactions()
        print(f"   ✅ Fetched {len(transactions)} records")
        
        # Create backup directory
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        print(f"\n3️⃣  Creating backup directory: {backup_dir}/")
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{backup_dir}/backup_{timestamp}.json"
        
        print(f"\n4️⃣  Saving to: {filename}")
        
        # Save to JSON
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=2, ensure_ascii=False)
        
        # Get file size
        file_size = os.path.getsize(filename)
        
        print("\n" + "=" * 70)
        print("✅ BACKUP COMPLETED!")
        print("=" * 70)
        print(f"\n📁 File: {filename}")
        print(f"📊 Records: {len(transactions)}")
        print(f"💾 Size: {file_size:,} bytes")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ BACKUP FAILED: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = backup_data()
    
    if not success:
        print("\n⚠️  Backup failed. Please check the errors above.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    else:
        input("\nPress Enter to exit...")
        sys.exit(0)