# Sheet Names
SHEET_TRANSACTIONS = 'Transactions'
SHEET_CAPSTERS = 'CapsterList'
SHEET_SUMMARY = 'Summary'
SHEET_CUSTOMERS = 'Customers'

# Services & Prices - Main Services
SERVICES_MAIN = {
    'potong': {'name': 'Potong Rambut', 'price': 25000},
    'potongcuci': {'name': 'Potong + Cuci', 'price': 30000},
    'PotongAnak' : {'name': 'Potong Anak', 'price': 20000},
    'PotongAnakCuci' : {'name': 'Potong & Cuci Anak', 'price': 25000},
    'PotongBapakAnak': {'name': 'Potong Bapak & Anak', 'price': 40000},
}

# Coloring Services - Sub Menu
SERVICES_COLORING = {
    'coloring_highlights': {'name': 'Highlights', 'price': 60000},
    'coloring_full': {'name': 'Full Color', 'price': 200000},
    'clack_color': {'name': 'Black', 'price': 40000},
    'coloring_bleaching': {'name': 'Bleaching', 'price': 45000},
}

METHOD_PAY = {
    'cash': {'name': '💵Tunai'},
    'qris': {'name': '📲Qris'},
}

PAYMENT_METHODS = {
    'cash': {'name': 'Cash', 'icon': '💵'},
    'qris': {'name': 'QRIS', 'icon': '📱'},
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
CB_BACK_WEKKLY_MENU = 'back_weekly_menu'

# Customer Menu
CB_CUSTOMER_MENU = 'customer_menu'
CB_ADD_CUSTOMER = 'add_customer'
CB_LIST_CUSTOMERS = 'list_customers'

#callback for capster
CB_REPORT_DAILY_CAPSTER = 'report_daily_capter'
CB_REPORT_WEEKLY_CAPSTER = 'report_weekly_capter'
CB_REPORT_MONTHLY_CAPSTER = 'report_monthly_capter'

BRANCHES = {
    'cabang_a': {
        'name': 'Cabang Denailla', 
        'location': 'Mojosari', 
        'short': 'Cabang A',
        'employees' : 2,
        'oprational_cost' : {
            'tempat' : 520000,
            'listrik air' : 400000,
            'wifi' : 15000,
            'karyawan_fixed' : 2500000,
        }, 
    },
    'cabang_b': {
        'name': 'Cabang Sumput', 
        'location': 'Sumput', 
        'short': 'Cabang B',
        'employees' : 2,
        'oprational_cost' : {
            'tempat' : 792000,
            'listrik air' : 350000,
            'wifi' : 30000,
        }
    },
}

OPRATIONAL_CONFIG = {
    'day_per_month' : 30,
    'week_per_month' : 4.33,
    'commision_rate' : 0.5
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

# Customer Messages
MSG_CUSTOMER_MENU = "👤 Menu Pelanggan\n\nPilih opsi di bawah:"
MSG_ADD_CUSTOMER_NAME = "✍️ Silakan masukkan nama pelanggan:"
MSG_ADD_CUSTOMER_PHONE = "📱 Silakan masukkan nomor telepon pelanggan:"
MSG_CUSTOMER_ADDED = "✅ Pelanggan '{name}' ({phone}) berhasil ditambahkan!"
MSG_CUSTOMER_LIST_HEADER = "👥 Daftar Pelanggan Terdaftar"

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



