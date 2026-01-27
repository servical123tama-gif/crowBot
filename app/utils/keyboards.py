"""
Keyboard Builders
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.config.constants import *
from app.services.auth_service import AuthService

class KeyboardBuilder:
    """Build inline keyboards"""
    
    @staticmethod
    def main_menu(user_id: int = None) -> InlineKeyboardMarkup:
        """Main menu keyboard - Dynamic based on user role"""
        keyboard = [
            [InlineKeyboardButton("➕ Tambah Transaksi", callback_data=CB_ADD_TRANSACTION)],
            [InlineKeyboardButton("🔄 Ganti Cabang", callback_data=CB_CHANGE_BRANCH)],
            [InlineKeyboardButton("📋 Lihat Laporan", callback_data=CB_REPORT_DAILY_CAPSTER)],
            [InlineKeyboardButton("📈 Laporan Mingguan", callback_data=CB_REPORT_WEEKLY_CAPSTER)],
            [InlineKeyboardButton("📅 Laporan Bulanan", callback_data=CB_REPORT_MONTHLY_CAPSTER)]
        ]
        
        # Tampilkan laporan bulanan hanya untuk owner/admin
        if user_id and AuthService.is_owner_or_admin(user_id):
            keyboard = (
                [InlineKeyboardButton("📊 Laporan Harian", callback_data=CB_REPORT_DAILY)],
                [InlineKeyboardButton("📈 Laporan Mingguan", callback_data=CB_REPORT_WEEKLY_BREAKDOWN)],
                [InlineKeyboardButton("📅 Laporan Bulanan 👑", callback_data=CB_REPORT_MONTHLY)],
                
            )
        
        return InlineKeyboardMarkup(keyboard)
    
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