"""
Report Generation Service
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd

from app.services.sheets_service import SheetsService
from app.utils.formatters import Formatter
from app.utils.week_calculator import WeekCalculator
from app.config.constants import *
from app.models.query import QueryResult # Import QueryResult

logger = logging.getLogger(__name__)

"""
Saat ini, setiap permintaan laporan (/monthly_report, /profit_report) memicu panggilan ke get_transactions_dataframe() yang membaca semua data dari Google Sheets. Ini lambat.

  Solusinya adalah membuat cache sederhana di ReportService. Kita akan menyimpan data transaksi dalam variabel _transactions_cache dan waktu pembaruan di _cache_timestamp.

  Saya akan membuat fungsi _get_or_fetch_transactions() yang akan:
   1. Memeriksa _cache_timestamp untuk melihat apakah cache kedaluwarsa (misalnya >5 menit).
   2. Jika cache baru, kembalikan data dari _transactions_cache secara instan.
   3. Jika kedaluwarsa, ambil data baru dari Google Sheets, perbarui cache dan timestamp, lalu kembalikan datanya.

  Fungsi generate_monthly_report dan generate_monthly_profit_report akan diubah untuk menggunakan fungsi _get_or_fetch_transactions(). Ini akan membuat laporan kedua dan seterusnya jauh lebih
  cepat.
"""

class ReportService:
    """Generate reports"""
    
    def __init__(self, sheets_service: SheetsService):
        try:
            logger.info("Initializing ReportService...")
            self.sheets = sheets_service
            self.week_calc = WeekCalculator()
            
            # --- CACHE ---
            self._transactions_cache = {}  # Dict to hold cache per year
            self._cache_timestamp = {}   # Dict to hold timestamp per year
            self.CACHE_DURATION = timedelta(minutes=5)
            # --- END CACHE ---

            # Capster alias map: name_lower -> [all known names_lower]
            self._capster_alias_map = {}

            logger.info("ReportService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReportService: {e}", exc_info=True)
            raise

    def _filter_by_capster(self, df: pd.DataFrame, capster_name: str) -> pd.DataFrame:
        """Filter DataFrame by capster name, expanding aliases if available."""
        name_lower = capster_name.lower()
        names_to_match = {name_lower}
        # Expand aliases: e.g. "Zidan" also matches "timingemma"
        for alias in self._capster_alias_map.get(name_lower, []):
            names_to_match.add(alias)
        return df[df['Capster'].str.lower().isin(names_to_match)]

    def _get_or_fetch_transactions(self, year: int) -> pd.DataFrame:
        """
        Fetches the transactions DataFrame from cache if available and not expired for a specific year,
        otherwise fetches from the source and updates the cache for that year.
        """
        now = datetime.now()

        # Check if cache is valid for the given year
        if year in self._transactions_cache and year in self._cache_timestamp:
            if now - self._cache_timestamp[year] < self.CACHE_DURATION:
                logger.info(f"Fetching transactions for year {year} from CACHE.")
                return self._transactions_cache[year]

        # Fetch from source if cache is invalid or expired
        logger.info(f"Cache for year {year} expired or empty. Fetching from Google Sheets.")
        df = self.sheets.get_transactions_dataframe(year=year)

        # Update cache for the specific year
        self._transactions_cache[year] = df
        self._cache_timestamp[year] = now

        return df

    def _build_capster_lookup(self) -> dict:
        """Build lookup dict: any known capster name/alias (lowercase) → {employment_type, commission_rate, monthly_salary, branch_id, name}."""
        lookup = {}
        try:
            for c in self.sheets.get_all_capsters():
                try:
                    salary = int(float(c.get('MonthlySalary') or 0))
                except (ValueError, TypeError):
                    salary = 0
                info = {
                    'employment_type': (c.get('EmploymentType') or 'mitra').lower().strip(),
                    'commission_rate': float(c.get('CommissionRate') or 0.5),
                    'monthly_salary': salary,
                    'branch_id': (c.get('BranchID') or '').strip(),
                    'name': c.get('Name', ''),
                }
                name_lower = (c.get('Name') or '').lower().strip()
                alias_lower = (c.get('Alias') or '').lower().strip()
                if name_lower:
                    lookup[name_lower] = info
                if alias_lower:
                    lookup[alias_lower] = info
        except Exception as e:
            logger.warning(f"_build_capster_lookup failed: {e}")
        return lookup
    
    def _get_week_range(self) -> tuple:
        """
        Get start and end date of current week (Monday to Sunday)
        Returns: (start_date, end_date)
        """
        today = datetime.now()
        
        # Get Monday of current week (weekday: 0=Monday, 6=Sunday)
        days_since_monday = today.weekday()  # 0=Monday, 1=Tuesday, ..., 6=Sunday
        monday = today - timedelta(days=days_since_monday)
        
        # Set to start of day (00:00:00)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Sunday is 6 days after Monday
        sunday = monday + timedelta(days=6)
        # Set to end of day (23:59:59)
        sunday = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        logger.info(f"Week range: {monday.strftime('%Y-%m-%d')} to {sunday.strftime('%Y-%m-%d')}")
        
        return monday, sunday
    
    def generate_weekly_breakdown(self, year: int = None, month: int = None, is_owner: bool = False) -> str:
        """
        Generate weekly breakdown report for a month
        Shows Week 1, Week 2, Week 3, Week 4 with totals
        """
        logger.info(f"Generating weekly breakdown, owner={is_owner}")
        
        try:
            if year is None or month is None:
                now = datetime.now()
                year = now.year
                month = now.month
            
            month_name = datetime(year, month, 1).strftime('%B %Y')
            
            # Get all weeks in month
            weeks = self.week_calc.get_weeks_in_month(year, month)
            
            if not weeks:
                return f"📊 Tidak ada data minggu untuk {month_name}"
            
            # Get all transactions for the year
            df = self._get_or_fetch_transactions(year=year)
            
            if df.empty:
                return f"📊 Tidak ada transaksi pada {month_name}"
            
            # Filter by month
            month_str = f"{year:04d}-{month:02d}"
            monthly = df[df['Date'].dt.strftime('%Y-%m') == month_str]
            
            if monthly.empty:
                return f"📊 Tidak ada transaksi pada {month_name}"
            
            # Generate report
            report = f"{REPORT_WEEKLY_BREAKDOWN_HEADER.format(month=month_name)}\n"
            report += f"⏰ Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}\n\n"
            
            total_month_revenue = 0
            total_month_transactions = 0
            
            # Process each week
            for week in weeks:
                week_num = week['week_num']
                start_date = week['start_date']
                end_date = week['end_date']
                
                # Filter transactions for this week
                week_df = monthly[
                    (monthly['Date'] >= start_date) & 
                    (monthly['Date'] <= end_date)
                ]
                
                
                week_revenue = week_df['Price'].sum() if not week_df.empty else 0
                week_count = len(week_df)
                
                total_month_revenue += week_revenue
                total_month_transactions += week_count
                
                # Week header
                report += f"📅 MINGGU {week_num} ({week['start_str']} - {week['end_str']})\n"
                report += f"{'─' * 40}\n"
                
                if week_df.empty:
                    report += "Tidak ada transaksi\n\n"
                    continue
                
                report += f"Transaksi: {week_count}\n"
                
                
                # Per branch
                if 'Branch' in week_df.columns:
                    by_branch = week_df.groupby('Branch')['Price'].sum()
                    report += "\nPer Cabang:\n"
                    for branch, amount in by_branch.items():
                        report += f"  🏢 {branch}: {Formatter.format_currency(amount)}\n"
                
                report += "\n"
            
            # Month summary
            report += "=" * 40 + "\n"
            report += f"📊 TOTAL BULAN {month_name.upper()}\n"
            report += "=" * 40 + "\n"
            report += f"Total Transaksi: {total_month_transactions}\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate weekly breakdown: {e}", exc_info=True)
            return f"❌ Gagal membuat laporan mingguan: {str(e)}"
    
    def generate_week_detail_report(self, year: int, month: int, week_num: int, is_owner: bool = False) -> str:
        """
        Generate detailed report for specific week
        """
        logger.info(f"Generating week {week_num} detail for {year}-{month}")
        
        try:
            month_name = datetime(year, month, 1).strftime('%B %Y')
            
            # Get week range
            start_date, end_date = self.week_calc.get_week_range(year, month, week_num)
            
            if start_date is None:
                return f"❌ Minggu {week_num} tidak valid untuk {month_name}"
            
            # Get transactions
            df = self.sheets.get_transactions_by_range(start_date, end_date)
            
            if df.empty:
                return f"📈 Tidak ada transaksi pada Minggu {week_num}\n({start_date.strftime('%d %b')} - {end_date.strftime('%d %b')})"
            
            gross_profit = df['Price'].sum()
            count = len(df)
            
            # Generate report
            report = f"{REPORT_WEEK_DETAIL_HEADER.format(week_num=week_num, month=month_name)}\n"
            report += f"📅 Periode: {start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')}\n"
            report += f"⏰ Generated: {datetime.now().strftime('%H:%M:%S')}\n\n"
            
            report += f"Total Transaksi: {count}\n"
            
            # Per branch
            if 'Branch' in df.columns:
                by_branch = df.groupby('Branch')['Price'].agg(['sum', 'count']).sort_values('sum', ascending=False)
                report += "Per Cabang:\n"
                
                for branch, row in by_branch.iterrows():
                    count_branch = int(row['count'])
                    sum_branch = row['sum']
                    report += f"  🏢 {branch}: {count_branch} transaksi ({Formatter.format_currency(sum_branch)})\n"
                
                report += "\n"
            
            # Top capsters with branch breakdown
            report += self._build_capster_branch_detail(df)

            # Top services
            top_services = df['Service'].value_counts().head(5)
            report += "\nLayanan Terpopuler:\n"
            for idx, (service, count) in enumerate(top_services.items(), 1):
                report += f"  {idx}. {service}: {count}x\n"

            # Daily breakdown with per-capster branch detail
            report += "\nPer Hari:\n"

            daily_totals = df.groupby(df['Date'].dt.date)['Price'].agg(['sum', 'count'])

            for date, row in daily_totals.iterrows():
                day_name = pd.Timestamp(date).strftime('%A')
                day_name_id = self._translate_day(day_name)
                count_day = int(row['count'])
                sum_day = row['sum']

                report += f"  📅 {day_name_id}, {pd.Timestamp(date).strftime('%d %b')}: {count_day} transaksi ({Formatter.format_currency(sum_day)})\n"

                day_df = df[df['Date'].dt.date == date]
                report += self._build_capster_branch_detail(day_df, indent="    ", show_header=False)
                report += "\n"
            
            logger.info("Weekly report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate week detail: {e}", exc_info=True)
            return f"❌ Gagal membuat laporan detail minggu: {str(e)}"
    
    def generate_daily_report(self, date: Optional[datetime] = None, user: Optional[str] = None) -> str:
        """Generate daily report for all or a specific capster."""
        if date is None:
            date = datetime.now()

        logger.info(f"Generating daily report for {date.strftime('%Y-%m-%d')}, user: {user}")

        try:
            df = self.sheets.get_transactions_by_date(date)

            if user:
                df = self._filter_by_capster(df, user)
            
            if df.empty:
                user_msg = f" untuk {user}" if user else ""
                return f"📊 Tidak ada transaksi{user_msg} pada {Formatter.format_date(date)}"
            
            total = df['Price'].sum()
            count = len(df)
            
            # Generate report header
            now = datetime.now()
            if user:
                report = f"{REPORT_DAILY_HEADERS_CAPSTER.format(date=Formatter.format_date(date), username=user)}\n\n"
                report += f"Capster: {user}\n"
            else:
                report = f"{REPORT_DAILY_HEADER.format(date=Formatter.format_date(date))}\n"
                report += f"⏰ Generated: {now.strftime('%H:%M:%S')}\n\n"

            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n\n"
            
            if not user:
                # Per branch breakdown (if column exists)
                if 'Branch' in df.columns:
                    logger.debug("Generating per-branch breakdown...")
                    by_branch = df.groupby('Branch')['Price'].agg(['sum', 'count'])
                    report += "Per Cabang:\n"
                    for branch, row in by_branch.iterrows():
                        count_branch = int(row['count'])
                        sum_branch = row['sum']
                        report += f"  🏢 {branch}: {count_branch} transaksi ({Formatter.format_currency(sum_branch)})\n"
                    report += "\n"

                # Per capster breakdown with branch detail
                logger.debug("Generating per-capster breakdown...")
                report += self._build_capster_branch_detail(df)

            # Top services
            logger.debug("Finding top services...")
            top_services = df['Service'].value_counts().head(3)
            if not top_services.empty:
                report += "\nLayanan Terpopuler:\n"
                for service, svc_count in top_services.items():
                    report += f"  • {service}: {svc_count}x\n"
            
            if not user and 'Payment_Method' in df.columns:
                payment_breakdown = df.groupby('Payment_Method')['Price'].sum()
                report += "\nMetode Pembayaran:\n"
                for method, amount in payment_breakdown.items():
                    report += f"  {method}: {Formatter.format_currency(amount)}\n"
            
            logger.info("Daily report generated successfully")
            return report
            
        except KeyError as e:
            logger.error(f"Column not found: {e}")
            return f"❌ Format data tidak valid: {e}"
            
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}", exc_info=True)
            return f"❌ Gagal membuat laporan harian: {str(e)}"
    
    def generate_weekly_report(self, user: Optional[str] = None) -> str:
        """Generate weekly report (Monday to Sunday of current week) for all or a specific capster."""
        logger.info(f"Generating weekly report, user: {user}")

        try:
            # Get current week range (Monday to Sunday)
            monday, sunday = self._get_week_range()

            logger.info(f"Fetching transactions from {monday} to {sunday}")
            df = self.sheets.get_transactions_by_range(monday, sunday)
            logger.info(f"Fetched {len(df)} transactions")

            if user:
                df = self._filter_by_capster(df, user)

            if df.empty:
                user_msg = f" untuk {user}" if user else ""
                week_str = f"{monday.strftime('%d %b')} - {sunday.strftime('%d %b %Y')}"
                return f"📈 Tidak ada transaksi minggu ini{user_msg}\n({week_str})"
            
            total = df['Price'].sum()
            count = len(df)
            
            # Calculate days with transactions
            unique_days = df['Date'].dt.date.nunique()
            avg_per_day = total / unique_days if unique_days > 0 else 0
            
            # Week info
            week_str = f"{monday.strftime('%d %b')} - {sunday.strftime('%d %b %Y')}"
            now = datetime.now()
            
            report = f"{REPORT_WEEKLY_HEADER}\n"
            report += f"📅 Periode: {week_str}\n"
            if user:
                report += f"👤 Capster: {user}\n"
            report += f"⏰ Generated: {now.strftime('%H:%M:%S')}\n\n"
            
            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n"
            report += f"Hari Operasional: {unique_days} hari\n"
            report += f"Rata-rata/hari: {Formatter.format_currency(avg_per_day)}\n\n"
            
            if not user:
                # Per branch breakdown (if exists)
                if 'Branch' in df.columns:
                    by_branch = df.groupby('Branch')['Price'].agg(['sum', 'count']).sort_values('sum', ascending=False)
                    report += "Per Cabang:\n"
                    for branch, row in by_branch.iterrows():
                        count_branch = int(row['count'])
                        sum_branch = row['sum']
                        report += f"  🏢 {branch}: {count_branch} transaksi ({Formatter.format_currency(sum_branch)})\n"
                    report += "\n"

            # Top services
            top_services = df['Service'].value_counts().head(5)
            report += "Layanan Terpopuler:\n"
            for idx, (service, svc_count) in enumerate(top_services.items(), 1):
                report += f"  {idx}. {service}: {svc_count}x\n"
            
            if not user:
                # Top capsters with branch breakdown
                report += "\n" + self._build_capster_branch_detail(df)

            if not user and 'Payment_Method' in df.columns:
                payment_breakdown = df.groupby('Payment_Method')['Price'].sum().sort_values(ascending=False)
                report += "\nMetode Pembayaran:\n"
                for method, amount in payment_breakdown.items():
                    pct = (amount / total * 100) if total > 0 else 0
                    report += f"  {method}: {Formatter.format_currency(amount)} ({pct:.1f}%)\n"

            # Daily breakdown
            daily_totals = df.groupby(df['Date'].dt.date)['Price'].agg(['sum', 'count'])
            report += "\nPer Hari:\n"
            for date, row in daily_totals.iterrows():
                day_name = pd.Timestamp(date).strftime('%A')
                day_name_id = self._translate_day(day_name)
                count_day = int(row['count'])
                sum_day = row['sum']
                report += f"  📅 {day_name_id}, {pd.Timestamp(date).strftime('%d %b')}: {count_day} transaksi ({Formatter.format_currency(sum_day)})\n"

            logger.info("Weekly report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate weekly report: {e}", exc_info=True)
            return f"❌ Gagal membuat laporan mingguan: {str(e)}"
    
    def _translate_day(self, english_day: str) -> str:
        """Translate English day name to Indonesian"""
        translation = {
            'Monday': 'Senin',
            'Tuesday': 'Selasa',
            'Wednesday': 'Rabu',
            'Thursday': 'Kamis',
            'Friday': 'Jumat',
            'Saturday': 'Sabtu',
            'Sunday': 'Minggu'
        }
        return translation.get(english_day, english_day)

    def _build_capster_branch_detail(self, df: pd.DataFrame, indent: str = "  ",
                                      show_header: bool = True) -> str:
        """Build per-capster breakdown with branch and service detail.

        Output format:
          ✂️ Zidan (8 layanan - Rp 240,000)
            🏢 Cabang A: 5 layanan (Rp 150,000)
               Potong Rambut 3x, Potong + Cuci 2x
            🏢 Cabang B: 3 layanan (Rp 90,000)
               Potong Rambut 2x, Potong Anak 1x
        """
        if df.empty or 'Capster' not in df.columns:
            return ""

        has_branch = 'Branch' in df.columns

        result = ""
        if show_header:
            result += f"{indent[:-2] if len(indent) > 2 else ''}Per Capster:\n"

        # Sort capsters by total revenue descending
        capster_totals = df.groupby('Capster')['Price'].agg(['sum', 'count']).sort_values('sum', ascending=False)

        for capster, totals in capster_totals.iterrows():
            cap_count = int(totals['count'])
            cap_sum = totals['sum']
            result += f"{indent}✂️ {capster} ({cap_count} layanan - {Formatter.format_currency(cap_sum)})\n"

            capster_df = df[df['Capster'] == capster]

            if has_branch:
                by_branch = capster_df.groupby('Branch')['Price'].agg(['sum', 'count']).sort_values('sum', ascending=False)
                for branch, brow in by_branch.iterrows():
                    b_count = int(brow['count'])
                    b_sum = brow['sum']
                    result += f"{indent}  🏢 {branch}: {b_count} layanan ({Formatter.format_currency(b_sum)})\n"

                    # Service breakdown per branch — one per line
                    branch_services = capster_df[capster_df['Branch'] == branch]['Service'].value_counts()
                    for svc, cnt in branch_services.items():
                        result += f"{indent}     - {svc} x{cnt}\n"
            else:
                # No branch column — just show services
                services = capster_df['Service'].value_counts()
                for svc, cnt in services.items():
                    result += f"{indent}  - {svc} x{cnt}\n"

        return result

    
    def generate_monthly_report(self, year: Optional[int] = None, month: Optional[int] = None, user: Optional[str] = None) -> str:
        """Generate monthly report for a specific month and year, for all or a specific capster."""
        logger.info(f"Generating monthly report for {month}/{year}, user: {user}")
        
        try:
            current_date = datetime.now()
            if year is None:
                year = current_date.year
            if month is None:
                month = current_date.month

            report_date = datetime(year, month, 1)
            month_str = report_date.strftime('%Y-%m')
            month_display = report_date.strftime('%B %Y')
            
            logger.debug(f"Fetching transactions for year {year}...")
            df = self._get_or_fetch_transactions(year=year)
            logger.info(f"Total transactions in sheet: {len(df)}")
            
            if df.empty:
                logger.info("No transactions found in sheet")
                return f"📅 Tidak ada transaksi pada {month_display}"
            
            # Filter by specific month and year
            logger.debug(f"Filtering for month: {month_str}")
            monthly = df[df['Date'].dt.strftime('%Y-%m') == month_str]
            logger.info(f"Transactions this month: {len(monthly)}")

            if user:
                monthly = self._filter_by_capster(monthly, user)

            if monthly.empty:
                user_msg = f" untuk {user}" if user else ""
                return f"📅 Tidak ada transaksi{user_msg} pada {month_display}"
            
            total = monthly['Price'].sum()
            count = len(monthly)
            
            # Calculate days for the given month, up to the current day if it's the current month
            if year == current_date.year and month == current_date.month:
                days = current_date.day
            else:
                days = (datetime(year, month % 12 + 1, 1) - datetime(year, month, 1)).days

            avg_per_day = total / days if days > 0 else 0
            
            if user:
                report = f"{REPORT_MONTHLY_HEADERS_CAPSTER.format(month=month_display, username=user)}\n\n"
                report += f"Capster: {user}\n"
            else:
                report = f"{REPORT_MONTHLY_HEADER.format(month=month_display)}\n"
                report += f"⏰ Generated: {current_date.strftime('%d %b %Y, %H:%M:%S')}\n\n"

            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n"
            report += f"Rata-rata/hari: {Formatter.format_currency(avg_per_day)}\n\n"
            
            if not user:
                # Per branch (if exists)
                if 'Branch' in monthly.columns:
                    by_branch = monthly.groupby('Branch')['Price'].agg(['sum', 'count']).sort_values('sum', ascending=False)
                    report += "Per Cabang:\n"
                    for branch, row in by_branch.iterrows():
                        count_branch = int(row['count'])
                        sum_branch = row['sum']
                        pct = (sum_branch / total * 100) if total > 0 else 0
                        report += f"  🏢 {branch}: {count_branch} transaksi ({Formatter.format_currency(sum_branch)}) - {pct:.1f}%\n"
                    report += "\n"
            
            # Ranking capster with branch breakdown
            if not user:
                report += self._build_capster_branch_detail(monthly)
            
            # Service breakdown
            service_breakdown = monthly.groupby('Service').agg({
                'Price': ['sum', 'count']
            }).sort_values(('Price', 'sum'), ascending=False)
            
            report += "\nBreakdown Layanan:\n"
            for service, row in service_breakdown.iterrows():
                total_service = row[('Price', 'sum')]
                count_service = int(row[('Price', 'count')])
                report += f"  • {service}: {count_service}x ({Formatter.format_currency(total_service)})\n"
            
            if not user and 'Payment_Method' in monthly.columns:
                payment_breakdown = monthly.groupby('Payment_Method')['Price'].sum().sort_values(ascending=False)
                report += "\nMetode Pembayaran:\n"
                for method, amount in payment_breakdown.items():
                    pct = (amount / total * 100) if total > 0 else 0
                    report += f"  {method}: {Formatter.format_currency(amount)} ({pct:.1f}%)\n"
            
            logger.info(f"Monthly report for {month_display} generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate monthly report for {month}/{year}: {e}", exc_info=True)
            return f"❌ Gagal membuat laporan bulanan: {str(e)}"

    
    def generate_monthly_profit_report(self, year: Optional[int] = None, month: Optional[int] = None) -> str:
        """Generate monthly profit report with per-branch breakdown for a specific month and year."""
        logger.info(f"Generating monthly profit report with per-branch breakdown for {month}/{year}")
        
        try:
            now = datetime.now()
            if year is None:
                year = now.year
            if month is None:
                month = now.month

            report_date = datetime(year, month, 1)
            month_display = report_date.strftime('%B %Y')
            
            profit_data_df = self.generate_monthly_profit_dataframe(year, month)

            if profit_data_df.empty:
                return f"💰 Tidak ada data transaksi atau kolom 'Branch' tidak ditemukan untuk {month_display}."

            # Fetch monthly transactions for per-capster display
            _df_all = self._get_or_fetch_transactions(year=year)
            _month_str = f"{year:04d}-{month:02d}"
            monthly_df = (
                _df_all[_df_all['Date'].dt.strftime('%Y-%m') == _month_str]
                if not _df_all.empty else pd.DataFrame()
            )
            capster_lookup = self._build_capster_lookup()

            # Extract overall data
            total_revenue = profit_data_df.loc['Overall', 'Revenue']
            total_operational_cost = profit_data_df.loc['Overall', 'Operational Cost']
            total_net_profit = profit_data_df.loc['Overall', 'Net Profit']

            # --- Report Formatting ---
            report = f"{REPORT_PROFIT_HEADER.format(month=month_display)}\n"
            report += f"⏰ Generated: {now.strftime('%d %b %Y, %H:%M:%S')}\n"

            # Overall Summary
            report += "\n" + "="*40 + "\n"
            report += "RINGKASAN KESELURUHAN\n"
            report += "="*40 + "\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total_revenue)}\n"
            report += f"Total Biaya Operasional: {Formatter.format_currency(total_operational_cost)}\n"
            profit_emoji = "✅" if total_net_profit >= 0 else "❌"
            report += f"{profit_emoji} Profit Bersih Total: {Formatter.format_currency(total_net_profit)}\n"

            # Per-branch details (dynamic)
            for branch_id, branch_config in BRANCHES.items():
                branch_short = branch_config.get('short', branch_id)
                if branch_short not in profit_data_df.index:
                    continue
                row = profit_data_df.loc[branch_short]
                revenue = row['Revenue']
                fixed_cost = row['Fixed Cost']
                commission_cost = row['Commission Cost']
                total_costs = row['Operational Cost']
                net_profit = row['Net Profit']

                report += "\n" + "-"*40 + "\n"
                report += f"DETAIL PROFIT {branch_short.upper()}\n"
                report += "-"*40 + "\n"
                report += f"  - Pendapatan: {Formatter.format_currency(revenue)}\n"
                # Hitung gaji tetap untuk branch ini (untuk display)
                seen_tetap_r: set = set()
                tetap_lines: list = []
                tetap_salary_total = 0
                for info in capster_lookup.values():
                    if (info['employment_type'] == 'tetap'
                            and info['branch_id'] == branch_id
                            and info['name']
                            and info['name'] not in seen_tetap_r):
                        tetap_lines.append((info['name'], info['monthly_salary']))
                        tetap_salary_total += info['monthly_salary']
                        seen_tetap_r.add(info['name'])

                non_karyawan_fixed = fixed_cost - tetap_salary_total

                report += "  - Biaya Operasional:\n"
                report += f"    - Fixed (operasional): {Formatter.format_currency(non_karyawan_fixed)}\n"

                # Gaji capster tetap assigned ke branch ini
                for cap_name, sal in tetap_lines:
                    report += f"    - Gaji {cap_name} (tetap): {Formatter.format_currency(sal)}\n"

                report += f"    - Total Komisi Mitra: {Formatter.format_currency(commission_cost)}\n"

                # Per-capster mitra commission breakdown
                if not monthly_df.empty and 'Capster' in monthly_df.columns and 'Branch' in monthly_df.columns:
                    branch_df_r = monthly_df[monthly_df['Branch'] == branch_short]
                    if not branch_df_r.empty:
                        for cap_name, cap_df in branch_df_r.groupby('Capster'):
                            cap_rev = cap_df['Price'].sum()
                            info = capster_lookup.get(cap_name.lower().strip())
                            if info and info['employment_type'] == 'mitra':
                                rate = info['commission_rate']
                                cap_com = cap_rev * rate
                                report += f"      • {cap_name} (mitra {rate*100:.0f}%): {Formatter.format_currency(cap_com)} dari {Formatter.format_currency(cap_rev)}\n"

                report += f"    - Total Biaya: {Formatter.format_currency(total_costs)}\n"
                profit_emoji_b = "✅" if net_profit >= 0 else "❌"
                report += f"  {profit_emoji_b} Profit Bersih {branch_short}: {Formatter.format_currency(net_profit)}\n"

            logger.info("Monthly profit report with breakdown generated successfully")
            return report

        except Exception as e:
            logger.error(f"Failed to generate monthly profit report: {e}", exc_info=True)
            return f"❌ Gagal membuat laporan profit bulanan: {str(e)}"
    
    def generate_monthly_profit_dataframe(self, year: int, month: int) -> pd.DataFrame:
        """
        Generate monthly profit data as a pandas DataFrame for a specific year and month.
        Includes revenue, costs, and profit per branch and overall.
        """
        logger.info(f"Generating monthly profit DataFrame for {month}/{year}")

        try:
            # Get all transactions for the specified year
            df = self._get_or_fetch_transactions(year=year)
            
            # Filter for the specific month and year
            month_str = f"{year:04d}-{month:02d}"
            monthly_df = df[df['Date'].dt.strftime('%Y-%m') == month_str]

            if monthly_df.empty or 'Branch' not in monthly_df.columns:
                logger.info(f"No transactions or 'Branch' column missing for {month_str}. Returning empty DataFrame.")
                return pd.DataFrame()

            # Build per-capster commission lookup once
            capster_lookup = self._build_capster_lookup()

            # Prepare results dictionary — loop all branches dynamically
            results = {}
            overall_revenue = 0
            overall_fixed = 0
            overall_commission = 0

            for branch_id, branch_config in BRANCHES.items():
                branch_short = branch_config.get('short', branch_id)
                branch_df = monthly_df[monthly_df['Branch'] == branch_short]
                revenue = branch_df['Price'].sum()

                costs_config = branch_config.get('operational_cost', {})
                # cost_karyawan dikecualikan karena dihitung dari monthly_salary capster tetap
                fixed_costs = sum(v for k, v in costs_config.items() if k != 'karyawan')

                # Gaji capster tetap yang assigned ke branch ini
                tetap_salary = sum(
                    info['monthly_salary']
                    for info in capster_lookup.values()
                    if info['employment_type'] == 'tetap'
                    and info['branch_id'] == branch_id
                    and info['name']  # hindari double count alias
                    # deduplikasi: hanya hitung sekali per nama unik
                )
                # Deduplicate: capster_lookup menyimpan nama + alias, hitung per nama unik saja
                seen_tetap = set()
                tetap_salary = 0
                for info in capster_lookup.values():
                    if (info['employment_type'] == 'tetap'
                            and info['branch_id'] == branch_id
                            and info['name']
                            and info['name'] not in seen_tetap):
                        tetap_salary += info['monthly_salary']
                        seen_tetap.add(info['name'])

                fixed_costs += tetap_salary

                # Per-capster commission: mitra × individual rate, tetap = 0
                commission_cost = 0.0
                if not branch_df.empty and 'Capster' in branch_df.columns:
                    for cap_name, cap_df in branch_df.groupby('Capster'):
                        info = capster_lookup.get(cap_name.lower().strip())
                        if info and info['employment_type'] == 'mitra':
                            commission_cost += cap_df['Price'].sum() * info['commission_rate']

                total_costs = fixed_costs + commission_cost
                net_profit = revenue - total_costs

                results[branch_short] = {
                    'Revenue': revenue,
                    'Fixed Cost': fixed_costs,
                    'Commission Cost': commission_cost,
                    'Operational Cost': total_costs,
                    'Net Profit': net_profit,
                }

                overall_revenue += revenue
                overall_fixed += fixed_costs
                overall_commission += commission_cost

            overall_operational = overall_fixed + overall_commission
            results['Overall'] = {
                'Revenue': overall_revenue,
                'Fixed Cost': overall_fixed,
                'Commission Cost': overall_commission,
                'Operational Cost': overall_operational,
                'Net Profit': overall_revenue - overall_operational,
            }

            # Convert results to DataFrame
            profit_df = pd.DataFrame.from_dict(results, orient='index')
            profit_df.index.name = 'Category'

            return profit_df

        except Exception as e:
            logger.error(f"Failed to generate monthly profit DataFrame for {month}/{year}: {e}", exc_info=True)
            return pd.DataFrame()



    def _filter_by_timeframe(self, df: pd.DataFrame, timeframe_str: str, now: datetime) -> pd.DataFrame:
        """Filter DataFrame by timeframe string."""
        if timeframe_str == "minggu ini":
            start_date, end_date = self._get_week_range()
            df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        elif timeframe_str == "bulan ini":
            month_str = now.strftime('%Y-%m')
            df = df[df['Date'].dt.strftime('%Y-%m') == month_str]
        elif timeframe_str == "hari ini":
            date_str = now.strftime('%Y-%m-%d')
            df = df[df['Date'].dt.strftime('%Y-%m-%d') == date_str]
        elif timeframe_str == "kemarin":
            yesterday = now - timedelta(days=1)
            date_str = yesterday.strftime('%Y-%m-%d')
            df = df[df['Date'].dt.strftime('%Y-%m-%d') == date_str]
        elif timeframe_str == "bulan lalu":
            first_day_of_current_month = now.replace(day=1)
            last_day_of_last_month = first_day_of_current_month - timedelta(days=1)
            month_str = last_day_of_last_month.strftime('%Y-%m')
            df = df[df['Date'].dt.strftime('%Y-%m') == month_str]
        elif timeframe_str == "minggu lalu":
            start_date, _ = self._get_week_range()
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(seconds=1)
            df = df[(df['Date'] >= prev_start) & (df['Date'] <= prev_end)]
        elif timeframe_str == "3 bulan terakhir":
            three_months_ago = now - timedelta(days=90)
            df = df[df['Date'] >= three_months_ago]
        return df

    def _build_capster_ranking(self, df: pd.DataFrame, limit: int = 10) -> str:
        """Build capster ranking context string."""
        if df.empty or 'Capster' not in df.columns:
            return ""
        by_capster = df.groupby('Capster').agg(
            revenue=('Price', 'sum'),
            count=('Price', 'count')
        ).sort_values('revenue', ascending=False).head(limit)

        lines = ["Ranking Capster:"]
        for idx, (capster, row) in enumerate(by_capster.iterrows(), 1):
            lines.append(f"  {idx}. {capster}: {int(row['count'])} layanan, pendapatan Rp {row['revenue']:,.0f}")
        return "\n".join(lines)

    def _build_branch_comparison(self, df: pd.DataFrame) -> str:
        """Build branch comparison context string."""
        if df.empty or 'Branch' not in df.columns:
            return ""
        by_branch = df.groupby('Branch').agg(
            revenue=('Price', 'sum'),
            count=('Price', 'count')
        ).sort_values('revenue', ascending=False)

        lines = ["Perbandingan Cabang:"]
        for branch, row in by_branch.iterrows():
            lines.append(f"  - {branch}: {int(row['count'])} transaksi, pendapatan Rp {row['revenue']:,.0f}")
        return "\n".join(lines)

    def _build_service_popularity(self, df: pd.DataFrame, limit: int = 10) -> str:
        """Build service popularity context string."""
        if df.empty or 'Service' not in df.columns:
            return ""
        by_service = df.groupby('Service').agg(
            count=('Price', 'count'),
            revenue=('Price', 'sum')
        ).sort_values('count', ascending=False).head(limit)

        lines = ["Layanan Terpopuler:"]
        for idx, (service, row) in enumerate(by_service.iterrows(), 1):
            lines.append(f"  {idx}. {service}: {int(row['count'])}x, pendapatan Rp {row['revenue']:,.0f}")
        return "\n".join(lines)

    def _build_profit_context(self, year: int, month: int, timeframe_str: str) -> str:
        """Build profit context string using generate_monthly_profit_dataframe."""
        try:
            profit_df = self.generate_monthly_profit_dataframe(year, month)
            if profit_df.empty:
                return "Data profit tidak tersedia untuk periode ini."

            lines = [f"Data Profit (bulan {month}/{year}):"]
            for category in profit_df.index:
                row = profit_df.loc[category]
                lines.append(f"  {category}:")
                lines.append(f"    Revenue: Rp {row['Revenue']:,.0f}")
                lines.append(f"    Biaya Operasional: Rp {row['Operational Cost']:,.0f}")
                lines.append(f"    Net Profit: Rp {row['Net Profit']:,.0f}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Failed to build profit context: {e}")
            return "Data profit tidak tersedia."

    def _build_daily_breakdown(self, df: pd.DataFrame) -> str:
        """Build daily breakdown context string."""
        if df.empty:
            return ""
        daily = df.groupby(df['Date'].dt.date).agg(
            revenue=('Price', 'sum'),
            count=('Price', 'count')
        ).sort_index()

        lines = ["Breakdown per Hari:"]
        for date, row in daily.iterrows():
            day_name = pd.Timestamp(date).strftime('%A')
            day_name_id = self._translate_day(day_name)
            lines.append(f"  {day_name_id}, {pd.Timestamp(date).strftime('%d %b')}: {int(row['count'])} transaksi, Rp {row['revenue']:,.0f}")
        return "\n".join(lines)

    def _build_payment_methods(self, df: pd.DataFrame) -> str:
        """Build payment method breakdown context string."""
        if df.empty or 'Payment_Method' not in df.columns:
            return ""
        by_payment = df.groupby('Payment_Method')['Price'].sum().sort_values(ascending=False)
        lines = ["Metode Pembayaran:"]
        for method, amount in by_payment.items():
            lines.append(f"  - {method}: Rp {amount:,.0f}")
        return "\n".join(lines)

    def generate_report_from_query(self, query_result: 'QueryResult') -> Optional[str]:
        """
        Filters data based on a QueryResult and returns a rich context string
        for Gemini to generate natural language response.
        """
        now = datetime.now()

        # Determine which year(s) data to fetch
        years_needed = set()
        if query_result.specific_dates:
            years_needed = {d.year for d in query_result.specific_dates}
        elif query_result.specific_date:
            years_needed.add(query_result.specific_date.year)
            if query_result.date_end:
                years_needed.add(query_result.date_end.year)
        elif query_result.specific_year:
            years_needed.add(query_result.specific_year)
        else:
            years_needed.add(now.year)

        # 1. Fetch base data (merge multiple years if needed)
        frames = []
        for y in years_needed:
            f = self._get_or_fetch_transactions(y)
            if not f.empty:
                frames.append(f)

        if not frames:
            return None
        df = pd.concat(frames).drop_duplicates() if len(frames) > 1 else frames[0]

        if df.empty:
            return None

        # 2. Filter by timeframe
        # Priority: multiple dates > date range > specific date > specific month > relative
        timeframe_str = query_result.timeframe_str or 'bulan ini'

        if query_result.specific_dates:
            # Filter to multiple discrete dates
            date_strs = [d.strftime('%Y-%m-%d') for d in query_result.specific_dates]
            df = df[df['Date'].dt.strftime('%Y-%m-%d').isin(date_strs)]
        elif query_result.specific_date and query_result.date_end:
            # Date range filter
            start_dt = query_result.specific_date
            end_dt = query_result.date_end.replace(hour=23, minute=59, second=59)
            df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]
        elif query_result.specific_date:
            # Filter to exact date
            target = query_result.specific_date
            date_str = target.strftime('%Y-%m-%d')
            df = df[df['Date'].dt.strftime('%Y-%m-%d') == date_str]
        elif query_result.specific_month and query_result.specific_year:
            # Filter to specific month
            month_str = f"{query_result.specific_year:04d}-{query_result.specific_month:02d}"
            df = df[df['Date'].dt.strftime('%Y-%m') == month_str]
        else:
            df = self._filter_by_timeframe(df, timeframe_str, now)

        # 3. Filter by capsters (with alias expansion)
        if query_result.capsters:
            capster_filter = set()
            alias_map = query_result.capster_alias_map or {}
            for name in query_result.capsters:
                name_lower = name.lower()
                capster_filter.add(name_lower)
                # Expand aliases: e.g. "Zidan" also matches "timingemma"
                for alias_name in alias_map.get(name_lower, []):
                    capster_filter.add(alias_name)
            df = df[df['Capster'].str.lower().isin(capster_filter)]

        # 4. Filter by branches
        if query_result.branches:
            branch_filter = [name.lower() for name in query_result.branches]
            df = df[df['Branch'].str.lower().isin(branch_filter)]

        # 5. Filter by payment methods
        if query_result.payment_methods and 'Payment_Method' in df.columns:
            pm_filter = [name.lower() for name in query_result.payment_methods]
            df = df[df['Payment_Method'].str.lower().isin(pm_filter)]

        if df.empty:
            return f"Data tidak ditemukan untuk periode '{timeframe_str}'."

        # 5. Build context string
        total_revenue = df['Price'].sum()
        total_transactions = len(df)
        report_type = query_result.report_type or 'general'
        limit = query_result.limit or 10

        context_parts = [
            f"Periode: {timeframe_str}",
            f"Total Pendapatan: Rp {total_revenue:,.0f}",
            f"Jumlah Transaksi: {total_transactions}",
        ]

        if query_result.capsters:
            context_parts.append(f"Filter Capster: {', '.join(query_result.capsters)}")
        if query_result.branches:
            context_parts.append(f"Filter Cabang: {', '.join(query_result.branches)}")
        if query_result.payment_methods:
            context_parts.append(f"Filter Metode Pembayaran: {', '.join(query_result.payment_methods)}")

        # Add report-type specific data
        if report_type in ('capster_ranking', 'general', 'monthly_summary', 'weekly_summary'):
            ranking = self._build_capster_ranking(df, limit)
            if ranking:
                context_parts.append(ranking)

        if report_type in ('branch_comparison', 'general', 'monthly_summary', 'weekly_summary'):
            comparison = self._build_branch_comparison(df)
            if comparison:
                context_parts.append(comparison)

        if report_type in ('service_popularity', 'general', 'monthly_summary'):
            popularity = self._build_service_popularity(df, limit)
            if popularity:
                context_parts.append(popularity)

        if report_type == 'profit':
            # Determine month for profit calculation
            if timeframe_str == 'bulan lalu':
                first_day = now.replace(day=1)
                last_month = first_day - timedelta(days=1)
                profit_context = self._build_profit_context(last_month.year, last_month.month, timeframe_str)
            else:
                profit_context = self._build_profit_context(year, now.month, timeframe_str)
            context_parts.append(profit_context)

        if report_type in ('daily_summary', 'weekly_summary', 'monthly_summary', 'general'):
            daily = self._build_daily_breakdown(df)
            if daily:
                context_parts.append(daily)

        # Always include payment method breakdown
        payments = self._build_payment_methods(df)
        if payments:
            context_parts.append(payments)

        return "\n\n".join(context_parts)

    def get_dynamic_capster_list(self, year: int = None) -> list:
        """Get unique capster names from transaction data."""
        if year is None:
            year = datetime.now().year
        try:
            df = self._get_or_fetch_transactions(year)
            if df.empty or 'Capster' not in df.columns:
                return []
            return sorted(df['Capster'].dropna().unique().tolist())
        except Exception as e:
            logger.error(f"Failed to get dynamic capster list: {e}")
            return []

    def get_branch_list(self) -> list:
        """Get branch names from constants."""
        return [branch['name'] for branch_id, branch in BRANCHES.items()]

        