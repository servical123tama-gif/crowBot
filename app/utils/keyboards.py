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
    CB_CAPSTER_MENU, CB_ADD_CAPSTER, CB_LIST_CAPSTERS, CB_REMOVE_CAPSTER,
    CB_CONFIRM_REMOVE_CAPSTER, CB_EDIT_CAPSTER, CB_MIGRATE_CAPSTER_NAMES,
    CB_TRANSACTION_AGAIN,
    CB_CONFIG_MENU, CB_CONFIG_SERVICES, CB_CONFIG_BRANCHES,
    CB_CONFIG_LIST_SERVICES, CB_CONFIG_ADD_SERVICE,
    CB_CONFIG_EDIT_SERVICE, CB_CONFIG_REMOVE_SERVICE, CB_CONFIG_CONFIRM_RM_SVC,
    CB_CONFIG_LIST_BRANCHES, CB_CONFIG_EDIT_BRANCH,
    CB_CONFIG_EDIT_BRANCH_COST, CB_CONFIG_EDIT_BRANCH_COMMISSION,
    CB_CONFIG_PRODUCTS, CB_CONFIG_LIST_PRODUCTS, CB_CONFIG_ADD_PRODUCT,
    CB_CONFIG_EDIT_PRODUCT, CB_CONFIG_REMOVE_PRODUCT, CB_CONFIG_CONFIRM_RM_PRD,
    CB_SELL_PRODUCT, CB_PRODUCT_SELECT, CB_PRODUCT_PAYMENT,
    BRANCHES, SERVICES_MAIN, SERVICES_COLORING, PAYMENT_METHODS, PRODUCTS
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
            [InlineKeyboardButton("🧴 Jual Produk", callback_data=CB_SELL_PRODUCT)],
            [InlineKeyboardButton("🔄 Ganti Cabang", callback_data=CB_CHANGE_BRANCH)],
            [InlineKeyboardButton("📋 Laporan Harian Saya", callback_data=CB_REPORT_DAILY_CAPSTER)],
            [InlineKeyboardButton("📈 Laporan Mingguan Saya", callback_data=CB_REPORT_WEEKLY_CAPSTER)],
            [InlineKeyboardButton("📅 Laporan Bulanan Saya", callback_data=CB_REPORT_MONTHLY_CAPSTER)]
        ]

        # Append owner/admin specific options (keep base items above)
        if AuthService.is_owner_or_admin(user_id):
            keyboard_rows = [
            [InlineKeyboardButton("📊 Laporan Harian Umum", callback_data=CB_REPORT_DAILY)],
            [InlineKeyboardButton("📈 Laporan Mingguan Umum", callback_data=CB_REPORT_WEEKLY_BREAKDOWN)],
            [InlineKeyboardButton("📅 Laporan Bulanan Umum", callback_data=CB_REPORT_MONTHLY)],
            [InlineKeyboardButton("💰 Laporan Profit", callback_data=CB_REPORT_PROFIT)],
            [InlineKeyboardButton("💈 Kelola Capster", callback_data=CB_CAPSTER_MENU)],
            [InlineKeyboardButton("👤 Menu Pelanggan", callback_data=CB_CUSTOMER_MENU)],
            [InlineKeyboardButton("⚙️ Pengaturan", callback_data=CB_CONFIG_MENU)],
            ]
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
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu", callback_data=CB_BACK_MAIN)])

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
    def transaction_success() -> InlineKeyboardMarkup:
        """Buttons after successful transaction"""
        keyboard = [
            [InlineKeyboardButton("➕ Transaksi Lagi", callback_data=CB_ADD_TRANSACTION)],
            [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data=CB_BACK_MAIN)],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def customer_menu(user_id: int) -> InlineKeyboardMarkup:
        """Customer menu keyboard - Dynamic based on user role"""
        keyboard = []
        if AuthService.is_owner_or_admin(user_id):
            keyboard.append([InlineKeyboardButton("👥 Daftar Pelanggan", callback_data=CB_LIST_CUSTOMERS)])
        else:
            keyboard.append([InlineKeyboardButton("➕ Tambah Pelanggan", callback_data=CB_ADD_CUSTOMER)])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu", callback_data=CB_BACK_MAIN)])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def capster_menu() -> InlineKeyboardMarkup:
        """Capster management menu keyboard (owner only)."""
        keyboard = [
            [InlineKeyboardButton("➕ Tambah Capster", callback_data=CB_ADD_CAPSTER)],
            [InlineKeyboardButton("📋 Daftar Capster", callback_data=CB_LIST_CAPSTERS)],
            [InlineKeyboardButton("🔄 Migrasi Nama Transaksi", callback_data=CB_MIGRATE_CAPSTER_NAMES)],
            [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data=CB_BACK_MAIN)],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def capster_list_keyboard(capsters) -> InlineKeyboardMarkup:
        """List capsters with edit and delete buttons per capster."""
        keyboard = []
        for c in capsters:
            keyboard.append([
                InlineKeyboardButton(
                    f"✏️ {c.name}",
                    callback_data=f"{CB_EDIT_CAPSTER}_{c.telegram_id}"
                ),
                InlineKeyboardButton(
                    "🗑️",
                    callback_data=f"{CB_REMOVE_CAPSTER}_{c.telegram_id}"
                ),
            ])
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Capster", callback_data=CB_CAPSTER_MENU)])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_remove_capster(telegram_id: int, name: str) -> InlineKeyboardMarkup:
        """Confirmation before removing a capster."""
        keyboard = [
            [InlineKeyboardButton(
                f"✅ Ya, hapus {name}",
                callback_data=f"{CB_CONFIRM_REMOVE_CAPSTER}_{telegram_id}"
            )],
            [InlineKeyboardButton("❌ Batal", callback_data=CB_LIST_CAPSTERS)],
        ]
        return InlineKeyboardMarkup(keyboard)

    # --- Config Keyboards ---

    @staticmethod
    def config_menu() -> InlineKeyboardMarkup:
        """Config main menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("📋 Kelola Layanan", callback_data=CB_CONFIG_SERVICES)],
            [InlineKeyboardButton("🧴 Kelola Produk", callback_data=CB_CONFIG_PRODUCTS)],
            [InlineKeyboardButton("🏢 Kelola Cabang", callback_data=CB_CONFIG_BRANCHES)],
            [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data=CB_BACK_MAIN)],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def config_services_menu() -> InlineKeyboardMarkup:
        """Services config menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("📋 Daftar Layanan", callback_data=CB_CONFIG_LIST_SERVICES)],
            [InlineKeyboardButton("➕ Tambah Layanan", callback_data=CB_CONFIG_ADD_SERVICE)],
            [InlineKeyboardButton("🔙 Kembali", callback_data=CB_CONFIG_MENU)],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def config_service_list(services_main: dict, services_coloring: dict) -> InlineKeyboardMarkup:
        """List all services with edit/delete buttons."""
        keyboard = []
        if services_main:
            keyboard.append([InlineKeyboardButton("── Layanan Utama ──", callback_data="noop")])
            for sid, data in services_main.items():
                keyboard.append([
                    InlineKeyboardButton(
                        f"✏️ {data['name']} - Rp {data['price']:,}",
                        callback_data=f"{CB_CONFIG_EDIT_SERVICE}_{sid}"
                    ),
                    InlineKeyboardButton("🗑️", callback_data=f"{CB_CONFIG_REMOVE_SERVICE}_{sid}"),
                ])
        if services_coloring:
            keyboard.append([InlineKeyboardButton("── Layanan Coloring ──", callback_data="noop")])
            for sid, data in services_coloring.items():
                keyboard.append([
                    InlineKeyboardButton(
                        f"✏️ {data['name']} - Rp {data['price']:,}",
                        callback_data=f"{CB_CONFIG_EDIT_SERVICE}_{sid}"
                    ),
                    InlineKeyboardButton("🗑️", callback_data=f"{CB_CONFIG_REMOVE_SERVICE}_{sid}"),
                ])
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=CB_CONFIG_SERVICES)])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def config_branch_list(branches: dict) -> InlineKeyboardMarkup:
        """List branches for config editing."""
        keyboard = []
        for bid, data in branches.items():
            keyboard.append([InlineKeyboardButton(
                f"✏️ {data['name']} ({data.get('short', '')})",
                callback_data=f"{CB_CONFIG_EDIT_BRANCH}_{bid}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=CB_CONFIG_MENU)])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def config_branch_costs(branch_id: str, branch_data: dict) -> InlineKeyboardMarkup:
        """Show branch cost items + commission as editable buttons."""
        keyboard = []
        costs = branch_data.get('operational_cost', {})
        for cost_key, cost_val in costs.items():
            keyboard.append([InlineKeyboardButton(
                f"✏️ {cost_key}: Rp {int(cost_val):,}",
                callback_data=f"{CB_CONFIG_EDIT_BRANCH_COST}_{branch_id}_{cost_key}"
            )])
        commission = branch_data.get('commission_rate', 0)
        keyboard.append([InlineKeyboardButton(
            f"✏️ Komisi: {commission * 100:.0f}%",
            callback_data=f"{CB_CONFIG_EDIT_BRANCH_COMMISSION}_{branch_id}"
        )])
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=CB_CONFIG_BRANCHES)])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_remove_service(service_id: str, service_name: str) -> InlineKeyboardMarkup:
        """Confirmation before removing a service."""
        keyboard = [
            [InlineKeyboardButton(
                f"✅ Ya, hapus {service_name}",
                callback_data=f"{CB_CONFIG_CONFIRM_RM_SVC}_{service_id}"
            )],
            [InlineKeyboardButton("❌ Batal", callback_data=CB_CONFIG_LIST_SERVICES)],
        ]
        return InlineKeyboardMarkup(keyboard)

    # --- Product Config Keyboards (Owner) ---

    @staticmethod
    def config_products_menu() -> InlineKeyboardMarkup:
        """Products config menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("📋 Daftar Produk", callback_data=CB_CONFIG_LIST_PRODUCTS)],
            [InlineKeyboardButton("➕ Tambah Produk", callback_data=CB_CONFIG_ADD_PRODUCT)],
            [InlineKeyboardButton("🔙 Kembali", callback_data=CB_CONFIG_MENU)],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def config_product_list(products: dict) -> InlineKeyboardMarkup:
        """List all products with edit/delete buttons."""
        keyboard = []
        for pid, data in products.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"✏️ {data['name']} - Rp {data['price']:,}",
                    callback_data=f"{CB_CONFIG_EDIT_PRODUCT}_{pid}"
                ),
                InlineKeyboardButton("🗑️", callback_data=f"{CB_CONFIG_REMOVE_PRODUCT}_{pid}"),
            ])
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=CB_CONFIG_PRODUCTS)])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_remove_product(product_id: str, product_name: str) -> InlineKeyboardMarkup:
        """Confirmation before removing a product."""
        keyboard = [
            [InlineKeyboardButton(
                f"✅ Ya, hapus {product_name}",
                callback_data=f"{CB_CONFIG_CONFIRM_RM_PRD}_{product_id}"
            )],
            [InlineKeyboardButton("❌ Batal", callback_data=CB_CONFIG_LIST_PRODUCTS)],
        ]
        return InlineKeyboardMarkup(keyboard)

    # --- Product Transaction Keyboards (Capster) ---

    @staticmethod
    def product_menu() -> InlineKeyboardMarkup:
        """Product selection keyboard for capster sale."""
        keyboard = []
        for product_id, product_data in PRODUCTS.items():
            name = product_data['name']
            price = product_data['price']
            callback = f"{CB_PRODUCT_SELECT}_{product_id}"
            button_text = f"{name} - Rp {price:,}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback)])
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu", callback_data=CB_BACK_MAIN)])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def product_payment_menu(product_id: str) -> InlineKeyboardMarkup:
        """Payment method selection for product sale."""
        keyboard = []
        for payment_id, payment_data in PAYMENT_METHODS.items():
            name = payment_data['name']
            callback = f"{CB_PRODUCT_PAYMENT}_{product_id}_{payment_id}"
            keyboard.append([InlineKeyboardButton(name, callback_data=callback)])
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Produk", callback_data=CB_SELL_PRODUCT)])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def product_sale_success() -> InlineKeyboardMarkup:
        """Buttons after successful product sale."""
        keyboard = [
            [InlineKeyboardButton("🧴 Jual Produk Lagi", callback_data=CB_SELL_PRODUCT)],
            [InlineKeyboardButton("➕ Tambah Transaksi", callback_data=CB_ADD_TRANSACTION)],
            [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data=CB_BACK_MAIN)],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def monthly_navigation_keyboard(current_year: int, current_month: int, report_type_prefix: str) -> InlineKeyboardMarkup:
        """
        Generates navigation buttons for monthly reports (Previous/Main Menu/Next).
        report_type_prefix should be CB_MONTHLY_NAV or CB_PROFIT_NAV.
        """
        from app.config.constants import MONTHS_ID

        # Calculate previous month
        prev_month_date = datetime(current_year, current_month, 1) - timedelta(days=1)
        prev_year = prev_month_date.year
        prev_month = prev_month_date.month
        prev_label = MONTHS_ID.get(prev_month, str(prev_month))

        # Calculate next month
        if current_month == 12:
            next_month_date = datetime(current_year + 1, 1, 1)
        else:
            next_month_date = datetime(current_year, current_month + 1, 1)
        next_year = next_month_date.year
        next_month = next_month_date.month
        next_label = MONTHS_ID.get(next_month, str(next_month))

        keyboard = [
            [
                InlineKeyboardButton(
                    f"⬅️ {prev_label}",
                    callback_data=f"{report_type_prefix}_{prev_year}_{prev_month}"
                ),
                InlineKeyboardButton("🏠 Menu", callback_data=CB_BACK_MAIN),
                InlineKeyboardButton(
                    f"{next_label} ➡️",
                    callback_data=f"{report_type_prefix}_{next_year}_{next_month}"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
