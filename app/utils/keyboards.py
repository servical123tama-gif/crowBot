"""
Keyboard Builders
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.config.constants import (
    CB_ADD_TRANSACTION, CB_CHANGE_BRANCH, CB_CUSTOMER_MENU, CB_REPORT_DAILY_CAPSTER,
    CB_REPORT_WEEKLY_CAPSTER, CB_REPORT_MONTHLY_CAPSTER, CB_REPORT_DAILY,
    CB_REPORT_WEEKLY_BREAKDOWN, CB_REPORT_MONTHLY, CB_REPORT_PROFIT,
    CB_LIST_CUSTOMERS, CB_ADD_CUSTOMER, CB_BRANCH, CB_SERVICE_MAIN,
    CB_COLORING_MENU, CB_SERVICE_COLORING, CB_PAYMENT, CB_BACK_SERVICE,
    CB_BACK_MAIN, CB_WEEK_SELECT,
    BRANCHES, SERVICES_MAIN, SERVICES_COLORING, PAYMENT_METHODS
)
from app.services.auth_service import AuthService
from datetime import datetime, timedelta

class KeyboardBuilder:
    """Build inline keyboards"""
    
    @staticmethod
    def main_menu(user_id: int = None) -> InlineKeyboardMarkup:
        """Main menu keyboard - Dynamic based on user role"""
        # Base keyboard for all authenticated users (capsters)
        keyboard_rows = [
            [InlineKeyboardButton("➕ Tambah Transaksi", callback_data=CB_ADD_TRANSACTION)],
            [InlineKeyboardButton("🔄 Ganti Cabang", callback_data=CB_CHANGE_BRANCH)],
            [InlineKeyboardButton("👤 Menu Pelanggan", callback_data=CB_CUSTOMER_MENU)],
            [InlineKeyboardButton("📋 Laporan Harian Saya", callback_data=CB_REPORT_DAILY_CAPSTER)],
            [InlineKeyboardButton("📈 Laporan Mingguan Saya", callback_data=CB_REPORT_WEEKLY_CAPSTER)],
            [InlineKeyboardButton("📅 Laporan Bulanan Saya", callback_data=CB_REPORT_MONTHLY_CAPSTER)]
        ]
        
        # Add owner/admin specific options
        if user_id and AuthService.is_owner_or_admin(user_id):
            # Append general reports and other admin options
            keyboard_rows = []
            keyboard_rows.append([InlineKeyboardButton("📊 Laporan Harian Umum", callback_data=CB_REPORT_DAILY)])
            keyboard_rows.append([InlineKeyboardButton("📈 Laporan Mingguan Umum", callback_data=CB_REPORT_WEEKLY_BREAKDOWN)])
            keyboard_rows.append([InlineKeyboardButton("📅 Laporan Bulanan Umum", callback_data=CB_REPORT_MONTHLY)])
            keyboard_rows.append([InlineKeyboardButton("💰 Laporan Profit", callback_data=CB_REPORT_PROFIT)])
            # Manajemen Stok Produk akan dihapus karena fiturnya di-revert
            # keyboard_rows.append([InlineKeyboardButton("📦 Manajemen Stok Produk", callback_data=CB_STOCK_MENU)]) # This button will be removed now
        
        return InlineKeyboardMarkup(keyboard_rows)
    
    @staticmethod
    def week_selection_menu(year: int, month: int) -> InlineKeyboardMarkup:
        """Week selection keyboard for monthly breakdown"""
        from app.utils.week_calculator import WeekCalculator
        
        weeks = WeekCalculator.get_weeks_in_month(year, month)
        keyboard = []
        
        for week in weeks:
            week_num = week['week_num']
            start_str = week['start_str']
            end_str = week['end_str']
            
            button_text = f"Minggu {week_num} ({start_str} - {end_str})"
            callback_data = f"{CB_WEEK_SELECT}_{year}_{month}_{week_num}"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # Back button
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu", callback_data=CB_BACK_MAIN)])
    
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def branch_menu() -> InlineKeyboardMarkup:
        """Branch selection keyboard"""
        keyboard = []
        
        for branch_id, branch_data in BRANCHES.items():
            name = branch_data['name']
            callback = f"{CB_BRANCH}_{branch_id}"
            keyboard.append([InlineKeyboardButton(name, callback_data=callback)])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def service_menu() -> InlineKeyboardMarkup:
        """Service selection keyboard"""
        keyboard = []
        
        # Main services
        for service_id, service_data in SERVICES_MAIN.items():
            name = service_data['name']
            price = service_data['price']
            service_id = service_id
            callback = f"{CB_SERVICE_MAIN}_{service_id}"
            
            button_text = f"{name} - Rp {price:,}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback)])
        
        # Coloring submenu
        keyboard.append([InlineKeyboardButton("🎨 Coloring (Lihat Pilihan)", callback_data=CB_COLORING_MENU)])
        
        # Back button
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=CB_BACK_MAIN)])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def coloring_menu() -> InlineKeyboardMarkup:
        """Coloring submenu keyboard"""
        keyboard = []
        
        for service_id, service_data in SERVICES_COLORING.items():
            name = service_data['name']
            price = service_data['price']
            callback = f"{CB_SERVICE_COLORING}_{service_id}"
            
            button_text = f"{name} - Rp {price:,}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback)])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Layanan", callback_data=CB_BACK_SERVICE)])
        
        return InlineKeyboardMarkup(keyboard)

    
    @staticmethod
    def payment_method_menu(service_id: str) -> InlineKeyboardMarkup:
        """Payment method selection keyboard"""
        keyboard = []
        
        # Payment method buttons
        for payment_id, payment_data in PAYMENT_METHODS.items():
            name = payment_data['name']
            # Format: payment_<service_id>_<payment_id>
            callback = f"{CB_PAYMENT}_{service_id}_{payment_id}"
            
            keyboard.append([InlineKeyboardButton(name, callback_data=callback)])
        
        # Back to service selection
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Layanan", callback_data=CB_ADD_TRANSACTION)])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button() -> InlineKeyboardMarkup:
        """Back to main menu button"""
        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu", callback_data=CB_BACK_MAIN)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def customer_menu(user_id: int) -> InlineKeyboardMarkup:
        """Customer menu keyboard - Dynamic based on user role"""
        keyboard = []
        if AuthService.is_owner_or_admin(user_id):
            keyboard.append([InlineKeyboardButton("👥 Daftar Pelanggan", callback_data=CB_LIST_CUSTOMERS)])
        else:
            keyboard.append([InlineKeyboardButton("➕ Tambah Pelanggan", callback_data=CB_ADD_CUSTOMER)])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data=CB_BACK_MAIN)])
        
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def monthly_navigation_keyboard(current_year: int, current_month: int, report_type_prefix: str) -> InlineKeyboardMarkup:
        """
        Generates navigation buttons for monthly reports (Previous/Main Menu/Next).
        report_type_prefix should be CB_MONTHLY_NAV or CB_PROFIT_NAV.
        """
        
        # Calculate previous month
        prev_month_date = datetime(current_year, current_month, 1) - timedelta(days=1)
        prev_year = prev_month_date.year
        prev_month = prev_month_date.month
        
        # Calculate next month
        if current_month == 12:
            next_month_date = datetime(current_year + 1, 1, 1)
        else:
            next_month_date = datetime(current_year, current_month + 1, 1)
        next_year = next_month_date.year
        next_month = next_month_date.month
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "⬅️ Sebelumnya", 
                    callback_data=f"{report_type_prefix}_{prev_year}_{prev_month}"
                ),
                InlineKeyboardButton("🏠 Menu Utama", callback_data=CB_BACK_MAIN),
                InlineKeyboardButton(
                    "Berikutnya ➡️", 
                    callback_data=f"{report_type_prefix}_{next_year}_{next_month}"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
