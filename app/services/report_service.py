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
            
            # Top capsters
            
            top_capsters = df.groupby('Capster')['Price'].sum().sort_values(ascending=False).head(5)
            report += "Top Capster:\n"
            for idx, (capster, amount) in enumerate(top_capsters.items(), 1):
                capster_count = df[df['Capster'] == capster].shape[0]
                report += f"  {idx}. {capster}: {capster_count} layanan ({Formatter.format_currency(amount)})\n"
            
            # Top services
            top_services = df['Service'].value_counts().head(5)
            report += "\nLayanan Terpopuler:\n"
            for idx, (service, count) in enumerate(top_services.items(), 1):
                report += f"  {idx}. {service}: {count}x\n"
            
            # Daily breakdown
            report += "\nPer Hari:\n"
            
            # --- OPTIMIZATION START ---
            # Group by both date and capster once to get all aggregates.
            daily_capster_agg = df.groupby([df['Date'].dt.date, 'Capster'])['Price'].agg(['sum', 'count']).sort_values(by=['Date', 'sum'], ascending=[True, False])
            
            # Group by just date to get daily totals.
            daily_totals = df.groupby(df['Date'].dt.date)['Price'].agg(['sum', 'count'])

            # Iterate through the daily totals to build the report string.
            for date, row in daily_totals.iterrows():
                day_name = pd.Timestamp(date).strftime('%A')
                day_name_id = self._translate_day(day_name)
                count_day = int(row['count'])
                sum_day = row['sum']
                
                report += f"  📅 {day_name_id}, {pd.Timestamp(date).strftime('%d %b')}: {count_day} transaksi ({Formatter.format_currency(sum_day)})\n"
                
                # Filter the pre-aggregated data for the current day.
                # This is much faster than grouping inside a loop.
                if date in daily_capster_agg.index:
                    day_capster_data = daily_capster_agg.loc[date]
                    
                    for capster, capster_row in day_capster_data.iterrows():
                        capster_count = int(capster_row['count'])
                        capster_sum = capster_row['sum']
                        report += f"  - {capster}: {capster_count} layanan ({Formatter.format_currency(capster_sum)})\n"
                    report += "\n"
            # --- OPTIMIZATION END ---
            
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
                
                # Per capster breakdown
                logger.debug("Generating per-capster breakdown...")
                by_capster = df.groupby('Capster')['Price'].agg(['sum', 'count'])
                report += "Per Capster:\n"
                for capster, row in by_capster.iterrows():
                    count_capster = int(row['count'])
                    sum_capster = row['sum']
                    report += f"  ✂️ {capster}: {count_capster} layanan ({Formatter.format_currency(sum_capster)})\n"

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
                # Top capsters
                top_capsters = df.groupby('Capster')['Price'].sum().sort_values(ascending=False).head(5)
                report += "\nTop Capster:\n"
                for idx, (capster, amount) in enumerate(top_capsters.items(), 1):
                    capster_count = df[df['Capster'] == capster].shape[0]
                    report += f"  {idx}. {capster}: {capster_count} layanan ({Formatter.format_currency(amount)})\n"
            
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
            
            # Ranking capster
            by_capster = monthly.groupby('Capster').agg({
                'Price': 'sum',
                'Service': 'count'
            }).sort_values('Price', ascending=False)
            
            if not user:
                report += "Ranking Capster:\n"
                for idx, (capster_name, row) in enumerate(by_capster.iterrows(), 1):
                    amount = row['Price']
                    count_capster = int(row['Service'])
                    report += f"  {idx}. {capster_name}: {count_capster} layanan ({Formatter.format_currency(amount)})\n"
            
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
                commission_rate = branch_config.get('commission_rate', 0)

                report += "\n" + "-"*40 + "\n"
                report += f"DETAIL PROFIT {branch_short.upper()}\n"
                report += "-"*40 + "\n"
                report += f"  - Pendapatan: {Formatter.format_currency(revenue)}\n"
                if commission_rate > 0:
                    report += "  - Biaya Operasional:\n"
                    report += f"    - Fixed: {Formatter.format_currency(fixed_cost)}\n"
                    report += f"    - Komisi ({commission_rate*100:.0f}%): {Formatter.format_currency(commission_cost)}\n"
                    report += f"    - Total Biaya: {Formatter.format_currency(total_costs)}\n"
                else:
                    report += f"  - Biaya Operasional (Fixed): {Formatter.format_currency(total_costs)}\n"
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
                fixed_costs = sum(costs_config.values())
                commission_rate = branch_config.get('commission_rate', 0)
                commission_cost = revenue * commission_rate
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

        # Always include payment method for summaries
        if report_type in ('monthly_summary', 'weekly_summary', 'general'):
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

        