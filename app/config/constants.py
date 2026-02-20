# Sheet Names
SHEET_TRANSACTIONS = 'Transactions'
SHEET_CAPSTERS = 'CapsterList'
SHEET_SUMMARY = 'Summary'
SHEET_CUSTOMERS = 'Customers'
SHEET_SERVICES = 'ServiceList'
SHEET_BRANCHES = 'BranchConfig'
SHEET_PRODUCTS = 'ProductList'
SHEET_SALARY = 'SalaryWithdrawal'

# Services & Prices - Main Services
SERVICES_MAIN = {
    'Potong': {'name': 'Potong Rambut', 'price': 25000},
    'PotongCuci': {'name': 'Potong + Cuci', 'price': 30000},
    'PotongAnak': {'name': 'Potong Anak', 'price': 20000},
    'PotongAnakCuci': {'name': 'Potong & Cuci Anak', 'price': 25000},
    'PotongBapakAnak': {'name': 'Potong Bapak & Anak', 'price': 40000},
}

# Coloring Services - Sub Menu
SERVICES_COLORING = {
    'ColoringHighlights': {'name': 'Highlights', 'price': 60000},
    'ColoringFull': {'name': 'Full Color', 'price': 200000},
    'BlackColor': {'name': 'Black', 'price': 40000},
    'ColoringBleaching': {'name': 'Bleaching', 'price': 45000},
}

METHOD_PAY = {
    'cash': {'name': '💵Tunai'},
    'qris': {'name': '📲Qris'},
}

PAYMENT_METHODS = {
    'cash': {'name': 'Cash', 'icon': '💵'},
    'qris': {'name': 'QRIS', 'icon': '📱'},
}

# Products (Pomade, Powder, etc.)
PRODUCTS = {
    'Pomade': {'name': 'Pomade', 'price': 55000},
    'Powder': {'name': 'Powder', 'price': 15000},
    'HairTonic': {'name': 'Hair Tonic', 'price': 25000},
}

# Combine all services for easy access
ALL_SERVICES = {**SERVICES_MAIN, **SERVICES_COLORING}

ROLE_OWNER = 'owner'
ROLE_CAPSTER = 'capster'
ROLE_ADMIN = 'admin'


# Callback Data Prefixes
CB_ADD_TRANSACTION = 'add_trans'
CB_SERVICE = 'service'
CB_SERVICE_MAIN = 'service_main'
CB_COLORING_MENU = 'coloring_menu'
CB_SERVICE_COLORING = 'service_coloring'
CB_REPORT_DAILY = 'report_daily'
CB_REPORT_WEEKLY = 'report_weekly'
CB_REPORT_MONTHLY = 'report_monthly'
CB_REPORT_PROFIT = 'report_profit'
CB_BACK_MAIN = 'back_main'
CB_BACK_SERVICE = 'back_service'
CB_TRANSACTION_AGAIN = 'transaction_again'
CB_PAYMENT = 'payment'
CB_BRANCH = 'branch'
CB_CHANGE_BRANCH = 'change_branch'
CB_MONTHLY_NAV = 'monthly_nav'
CB_PROFIT_NAV = 'profit_nav'



#repot weekly
CB_REPORT_WEEKLY_BREAKDOWN = 'report_weekly_breakdown'
CB_WEEK_SELECT = 'week_select'
CB_BACK_WEEKLY_MENU = 'back_weekly_menu'

# Customer Menu
CB_CUSTOMER_MENU = 'customer_menu'
CB_ADD_CUSTOMER = 'add_customer'
CB_LIST_CUSTOMERS = 'list_customers'

# Capster Management
CB_CAPSTER_MENU = 'capster_menu'
CB_ADD_CAPSTER = 'add_capster'
CB_LIST_CAPSTERS = 'list_capsters'
CB_REMOVE_CAPSTER = 'remove_capster'
CB_CONFIRM_REMOVE_CAPSTER = 'confirm_rm_capster'
CB_EDIT_CAPSTER = 'edit_capster'
CB_MIGRATE_CAPSTER_NAMES = 'migrate_capster_names'

#callback for capster
CB_REPORT_DAILY_CAPSTER = 'report_daily_capster'
CB_REPORT_WEEKLY_CAPSTER = 'report_weekly_capster'
CB_REPORT_MONTHLY_CAPSTER = 'report_monthly_capster'

# Config Management Callbacks
CB_CONFIG_MENU = 'config_menu'
CB_CONFIG_SERVICES = 'config_services'
CB_CONFIG_BRANCHES = 'config_branches'
CB_CONFIG_LIST_SERVICES = 'config_list_svc'
CB_CONFIG_ADD_SERVICE = 'config_add_svc'
CB_CONFIG_EDIT_SERVICE = 'config_edit_svc'
CB_CONFIG_REMOVE_SERVICE = 'config_rm_svc'
CB_CONFIG_CONFIRM_RM_SVC = 'config_crm_svc'
CB_CONFIG_LIST_BRANCHES = 'config_list_br'
CB_CONFIG_EDIT_BRANCH = 'config_edit_br'
CB_CONFIG_EDIT_BRANCH_COST = 'config_ebc'
CB_CONFIG_EDIT_BRANCH_COMMISSION = 'config_ebcm'

# Product Config Callbacks (Owner CRUD)
CB_CONFIG_PRODUCTS = 'config_products'
CB_CONFIG_LIST_PRODUCTS = 'config_list_prd'
CB_CONFIG_ADD_PRODUCT = 'config_add_prd'
CB_CONFIG_EDIT_PRODUCT = 'config_edit_prd'
CB_CONFIG_REMOVE_PRODUCT = 'config_rm_prd'
CB_CONFIG_CONFIRM_RM_PRD = 'config_crm_prd'

# Product Transaction Callbacks (Capster)
CB_SELL_PRODUCT = 'sell_product'
CB_PRODUCT_SELECT = 'prd_sel'
CB_PRODUCT_PAYMENT = 'prd_pay'

# Salary Management Callbacks
CB_SALARY_MENU = 'salary_menu'
CB_SALARY_CAPSTER = 'salary_capster'
CB_SALARY_WITHDRAW = 'salary_withdraw'
CB_SALARY_HISTORY = 'salary_history'
CB_SALARY_PERIOD_WEEK = 'salary_period_week'
CB_SALARY_PERIOD_MONTH = 'salary_period_month'

BRANCHES = {
    'cabang_a': {
        'name': 'Cabang Denailla',
        'location': 'Mojosari',
        'short': 'Cabang A',
        'employees': 2,
        'commission_rate': 0,
        'operational_cost': {
            'tempat': 520000,
            'listrik air': 400000,
            'wifi': 15000,
            'karyawan_fixed': 2500000,
        },
    },
    'cabang_b': {
        'name': 'Cabang Sumput',
        'location': 'Sumput',
        'short': 'Cabang B',
        'employees': 2,
        'commission_rate': 0.5,
        'operational_cost': {
            'tempat': 792000,
            'listrik air': 350000,
            'wifi': 30000,
            'karyawan_fixed': 0,
        }
    },
}

OPERATIONAL_CONFIG = {
    'day_per_month': 30,
    'week_per_month': 4.33,
    'commission_rate': 0.5
}

# Messages
MSG_UNAUTHORIZED = "⛔ Maaf, Anda tidak memiliki akses ke bot ini.\nUser ID Anda: {user_id}"
MSG_WELCOME = """👋 Hallo Bruh {username}, Semoga Harimu Lebih semangat
Selamat datang di {bot_name} !
Silakan pilih menu di bawah:"""
MSG_UNAUTHORIZED_FEATURE = "⛔ Maaf, fitur ini hanya untuk Owner/Admin.\n\n💡 Hubungi owner untuk akses."

MSG_TRANSACTION_SUCCESS = """✅ Transaksi berhasil dicatat!

📋 Detail:
- Layanan: {service}
- Harga: {currency} {price:,}
- Capster: {capster}
- Branch: {branch}
- Payment Method: {payment_method}
- Waktu: {time}"""

MSG_SELECT_PAYMENT = """💰 Pilih Metode Pembayaran

📋 Layanan: {service}
💵 Total: {currency} {price:,}

Silakan pilih metode pembayaran:"""

# Report Headers
REPORT_DAILY_HEADER = "📊 LAPORAN HARIAN - {date}"
REPORT_WEEKLY_HEADER = "📈 LAPORAN MINGGUAN (7 Hari Terakhir)"
REPORT_MONTHLY_HEADER = "📅 LAPORAN BULANAN - {month}"
REPORT_PROFIT_HEADER = "💰 LAPORAN PROFIT BULANAN - {month}"

REPORT_WEEKLY_BREAKDOWN_HEADER = 'LAPORAN MINGGUAN - {month}'
REPORT_WEEK_DETAIL_HEADER = 'MINGGU {week_num} - {month}'

REPORT_DAILY_HEADERS_CAPSTER = "📊 LAPORAN HARIAN CAPSTER {username} - {date}"
REPORT_WEEKLY_HEADERS_CAPSTER = "📈 LAPORAN MINGGUAN CAPSTER {username} (7 Hari Terakhir)"
REPORT_MONTHLY_HEADERS_CAPSTER = "📅 LAPORAN BULANAN CAPSTER {username} - {month}"

#branch
MSG_SELECT_BRANCH = """🏢 Pilih Cabang Hari Ini

Halo {capster}! 👋

Anda bekerja di cabang mana hari ini?
Pilihan ini akan tersimpan untuk hari ini."""

MSG_BRANCH_CHANGED = """✅ Cabang berhasil diubah!

🏢 Cabang saat ini: {branch}
📅 Tanggal: {date}

Semua transaksi hari ini akan tercatat di cabang ini."""

MSG_CURRENT_BRANCH = """📍 Cabang Saat Ini

🏢 {branch}
📅 {date}
👤 {capster}

Ingin ganti cabang?"""

# Capster Messages
MSG_CAPSTER_MENU = "💈 Menu Kelola Capster\n\nPilih opsi di bawah:"
MSG_ADD_CAPSTER_NAME = "✍️ Silakan masukkan nama capster:\n\n💡 Ketik /cancel untuk membatalkan."
MSG_ADD_CAPSTER_ID = "🔢 Silakan masukkan Telegram User ID capster:"
MSG_ADD_CAPSTER_ALIAS = "📛 Masukkan nama Telegram capster ini (nama di transaksi lama).\nKetik /skip jika tidak ada:"
MSG_CAPSTER_ADDED = "✅ Capster '{name}' (ID: {telegram_id}) berhasil ditambahkan!"
MSG_CAPSTER_REMOVED = "✅ Capster '{name}' berhasil dihapus."
MSG_CAPSTER_LIST_HEADER = "💈 Daftar Capster Terdaftar"
MSG_CAPSTER_LIST_EMPTY = "📭 Belum ada capster terdaftar.\n\nGunakan menu \"Tambah Capster\" untuk mendaftarkan capster baru."
MSG_EDIT_CAPSTER_NAME = "✍️ Masukkan nama baru (atau /skip untuk tidak mengubah):"
MSG_EDIT_CAPSTER_ALIAS = "📛 Masukkan alias baru (atau /skip untuk tidak mengubah):"
MSG_CAPSTER_UPDATED = "✅ Data capster berhasil diperbarui!"

# Config Messages
MSG_CONFIG_MENU = "⚙️ Menu Pengaturan\n\nKelola layanan, produk, dan cabang:"
MSG_CONFIG_SERVICES_MENU = "📋 Menu Layanan\n\nPilih opsi:"
MSG_CONFIG_BRANCHES_MENU = "🏢 Menu Cabang\n\nPilih cabang untuk edit:"
MSG_CONFIG_PRODUCTS_MENU = "🧴 Menu Produk\n\nPilih opsi:"
MSG_SELECT_PRODUCT = "🧴 Pilih Produk untuk Dijual:"
MSG_PRODUCT_SELECT_PAYMENT = """💰 Pilih Metode Pembayaran

🧴 Produk: {product}
💵 Total: {currency} {price:,}

Silakan pilih metode pembayaran:"""

# Customer Messages
MSG_CUSTOMER_MENU = "👤 Menu Pelanggan\n\nPilih opsi di bawah:"
MSG_ADD_CUSTOMER_NAME = "✍️ Silakan masukkan nama pelanggan:\n\n💡 Ketik /cancel untuk membatalkan."
MSG_ADD_CUSTOMER_PHONE = "📱 Silakan masukkan nomor telepon pelanggan:"
MSG_CUSTOMER_ADDED = "✅ Pelanggan '{name}' ({phone}) berhasil ditambahkan!"
MSG_CUSTOMER_LIST_HEADER = "👥 Daftar Pelanggan Terdaftar"

# Salary Messages
MSG_SALARY_MENU = "💰 Menu Gaji Capster\n\nPilih capster:"

# Date Formats
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DISPLAY_DATE_FORMAT = '%d %B %Y'
DISPLAY_TIME_FORMAT = '%H:%M'

# Month Mappings
MONTHS_ID = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

MONTHS_ID_REV = {
    'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6,
    'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
}



