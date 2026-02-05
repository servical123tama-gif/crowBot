"""
One-time migration script to move transactions from a single 'Transactions' sheet
to multiple sheets, one for each month of the year 2026.

This revised script ensures that all 12 monthly sheets for 2026 are created,
even if no data exists for a particular month.
"""
import logging
import time
import pandas as pd
from gspread.exceptions import WorksheetNotFound, APIError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Adjust path to import from the app
import sys
import os
sys.path.append(os.getcwd())

from app.services.sheets_service import SheetsService
from app.config.constants import SHEET_TRANSACTIONS, SHEET_CAPSTERS, SHEET_SUMMARY, MONTHS_ID

def migrate_data_force_2026():
    """
    Main function to perform the data migration.
    It ensures all sheets for 2026 are created.
    """
    logging.info("Starting data migration for year 2026...")
    
    try:
        sheets_service = SheetsService()
        sheet_file = sheets_service.sheet
    except Exception as e:
        logging.error(f"❌ Failed to connect to Google Sheets. Please check your credentials. Error: {e}")
        return

    # 1. Try to fetch data from the original 'Transactions' sheet
    main_df = pd.DataFrame()
    try:
        logging.info(f"Attempting to fetch data from '{SHEET_TRANSACTIONS}' sheet...")
        worksheet = sheet_file.worksheet(SHEET_TRANSACTIONS)
        records = worksheet.get_all_records()
        if records:
            main_df = pd.DataFrame(records)
            main_df['Date'] = pd.to_datetime(main_df['Date'])
            logging.info(f"Successfully fetched {len(main_df)} total transactions from '{SHEET_TRANSACTIONS}'.")
        else:
            logging.info(f"'{SHEET_TRANSACTIONS}' sheet is empty.")
    except WorksheetNotFound:
        logging.warning(f"⚠️ Original '{SHEET_TRANSACTIONS}' sheet not found. It might have been backed up already. Will proceed to create 2026 sheets.")
    except Exception as e:
        logging.error(f"❌ Could not read from '{SHEET_TRANSACTIONS}'. Error: {e}")
    
    # Year to process is hardcoded to 2026
    YEAR = 2026
    HEADERS = ['Date', 'Capster', 'Service', 'Price', 'Payment_Method', 'Branch']
    


    # 2. Loop through each month of 2026 and ensure sheets exist
    for month_num, month_name in MONTHS_ID.items():
        sheet_name = f"{month_name} {YEAR}"
        logging.info(f"--- Processing {sheet_name} ---")

        try:
            # Check if sheet exists
            worksheet = sheet_file.worksheet(sheet_name)
            logging.info(f"Sheet '{sheet_name}' already exists. Skipping creation.")
        except WorksheetNotFound:
            # If not, create it
            logging.info(f"Sheet '{sheet_name}' not found. Creating it...")
            try:
                worksheet = sheet_file.add_worksheet(title=sheet_name, rows="100", cols="20")
                worksheet.update('A1:F1', [HEADERS])
                logging.info(f"✅ Successfully created '{sheet_name}' with headers.")
            except APIError as e:
                logging.error(f"❌ API Error creating sheet '{sheet_name}': {e}. Check your permissions.")
                continue # Skip to next month
        except Exception as e:
            logging.error(f"❌ An unexpected error occurred for sheet '{sheet_name}': {e}")
            continue # Skip to next month

        # Now, check if there is data to write to this sheet
        if not main_df.empty:
            month_df = main_df[
                (main_df['Date'].dt.year == YEAR) &
                (main_df['Date'].dt.month == month_num)
            ]

            if not month_df.empty:
                logging.info(f"Found {len(month_df)} transactions for {month_name}. Writing to sheet...")
                # Append data (assuming headers are already there)
                # Using update is safer for one-time migration than append_rows in a loop
                try:
                    # Get current data in sheet to append after it
                    existing_data = worksheet.get_all_records()
                    start_row = len(existing_data) + 2 # +1 for header, +1 for next row
                    
                    data_to_write = month_df.astype(str).values.tolist()
                    worksheet.update(f'A{start_row}', data_to_write)
                    logging.info(f"✅ Successfully wrote {len(month_df)} transactions to '{sheet_name}'.")
                except Exception as e:
                    logging.error(f"❌ Failed to write data to '{sheet_name}': {e}")
        
        # Be nice to Google's API
        time.sleep(5)

    # 3. Rename the old 'Transactions' sheet if it still exists
    try:
        original_sheet = sheet_file.worksheet(SHEET_TRANSACTIONS)
        logging.info(f"Renaming original '{SHEET_TRANSACTIONS}' sheet to 'Transactions_Backup'...")
        original_sheet.update_title("Transactions_Backup")
        logging.info("✅ Original sheet successfully renamed.")
    except WorksheetNotFound:
        logging.info(f"✅ Original '{SHEET_TRANSACTIONS}' sheet was already renamed or removed, which is OK.")
    except Exception as e:
        logging.error(f"❌ Could not rename the original sheet. It might need to be done manually. Error: {e}")

    logging.info("\n🎉 Migration script finished! Please check your Google Sheet for the 12 monthly sheets of 2026.")

if __name__ == "__main__":
    print("===================================================================")
    print("  Google Sheets Migration Script for Monthly Sheets (Force 2026)")
    print("===================================================================")
    print("This script will:")
    print("1. Ensure that a sheet exists for every month of 2026 (Jan - Dec).")
    print("2. If data for 2026 exists in the 'Transactions' sheet, it will be moved.")
    print("3. Rename the old 'Transactions' sheet to 'Transactions_Backup' if it exists.")
    print("\nIMPORTANT: This script is safe to run multiple times.")
    
    answer = input("\nDo you want to continue? (y/n): ")
    if answer.lower() == 'y':
        migrate_data_force_2026()
    else:
        print("Migration cancelled.")