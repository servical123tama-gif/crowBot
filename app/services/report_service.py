"""
Report Generation Service
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

from app.services.sheets_service import SheetsService
from app.utils.formatters import Formatter
from app.utils.week_calculator import WeekCalculator
from app.config.constants import *

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
            self._transactions_cache = None
            self._cache_timestamp = None
            self.CACHE_DURATION = timedelta(minutes=5)
            # --- END CACHE ---

            logger.info("ReportService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReportService: {e}", exc_info=True)
            raise

    def _get_or_fetch_transactions(self) -> pd.DataFrame:
        """
        Fetches the transactions DataFrame from cache if available and not expired,
        otherwise fetches from the source and updates the cache.
        """
        now = datetime.now()
        
        # Check if cache is valid
        if self._transactions_cache is not None and self._cache_timestamp is not None:
            if now - self._cache_timestamp < self.CACHE_DURATION:
                logger.info("Fetching transactions from CACHE.")
                return self._transactions_cache

        # Fetch from source if cache is invalid or expired
        logger.info("Cache expired or empty. Fetching transactions from Google Sheets.")
        df = self.sheets.get_transactions_dataframe()
        
        # Update cache
        self._transactions_cache = df
        self._cache_timestamp = now
        
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
            
            # Get all transactions for the month
            df = self._get_or_fetch_transactions()
            
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
    
    def generate_daily_report(self, date: Optional[datetime] = None) -> str:
        """Generate daily report"""
        if date is None:
            date = datetime.now()
        
        logger.info(f"Generating daily report for {date.strftime('%Y-%m-%d')}")
        
        try:
            df = self.sheets.get_transactions_by_date(date)
            logger.info(f"Fetched {len(df)} transactions")
            
            if df.empty:
                logger.info("No transactions found for this date")
                return f"📊 Tidak ada transaksi pada {Formatter.format_date(date)}"
            
            total = df['Price'].sum()
            count = len(df)
            
            logger.info(f"Total: Rp {total:,}, Count: {count}")
            
            # Generate report header
            now = datetime.now()
            report = f"{REPORT_DAILY_HEADER.format(date=Formatter.format_date(date))}\n"
            report += f"⏰ Generated: {now.strftime('%H:%M:%S')}\n\n"
            
            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n\n"
            
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
                for service, count in top_services.items():
                    report += f"  • {service}: {count}x\n"
            
            # Payment methods breakdown (if column exists)
            if 'Payment_Method' in df.columns:
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
    
    def generate_weekly_report(self) -> str:
        """Generate weekly report (Monday to Sunday of current week)"""
        logger.info("Generating weekly report")
        
        try:
            # Get current week range (Monday to Sunday)
            monday, sunday = self._get_week_range()
            
            logger.info(f"Fetching transactions from {monday} to {sunday}")
            df = self.sheets.get_transactions_by_range(monday, sunday)
            logger.info(f"Fetched {len(df)} transactions")
            
            if df.empty:
                logger.info("No transactions this week")
                week_str = f"{monday.strftime('%d %b')} - {sunday.strftime('%d %b %Y')}"
                return f"📈 Tidak ada transaksi minggu ini\n({week_str})"
            
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
            report += f"⏰ Generated: {now.strftime('%H:%M:%S')}\n\n"
            
            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n"
            report += f"Hari Operasional: {unique_days} hari\n"
            report += f"Rata-rata/hari: {Formatter.format_currency(avg_per_day)}\n\n"
            
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
            for idx, (service, count) in enumerate(top_services.items(), 1):
                report += f"  {idx}. {service}: {count}x\n"
            
            # Top capsters
            top_capsters = df.groupby('Capster')['Price'].sum().sort_values(ascending=False).head(5)
            report += "\nTop Capster:\n"
            for idx, (capster, amount) in enumerate(top_capsters.items(), 1):
                # Count transactions per capster
                capster_count = df[df['Capster'] == capster].shape[0]
                report += f"  {idx}. {capster}: {capster_count} layanan ({Formatter.format_currency(amount)})\n"
            
            # Daily breakdown
            daily_totals = df.groupby(df['Date'].dt.date)['Price'].agg(['sum', 'count'])
            report += "\nPer Hari:\n"
            for date, row in daily_totals.iterrows():
                day_name = pd.Timestamp(date).strftime('%A')  # Monday, Tuesday, etc
                day_name_id = self._translate_day(day_name)  # Senin, Selasa, etc
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
    
    def generate_monthly_report(self, year: Optional[int] = None, month: Optional[int] = None) -> str:
        """Generate monthly report for a specific month and year"""
        logger.info(f"Generating monthly report for {month}/{year}")
        
        try:
            current_date = datetime.now()
            if year is None:
                year = current_date.year
            if month is None:
                month = current_date.month

            report_date = datetime(year, month, 1)
            month_str = report_date.strftime('%Y-%m')
            month_display = report_date.strftime('%B %Y')
            
            logger.debug("Fetching all transactions...")
            df = self._get_or_fetch_transactions()
            logger.info(f"Total transactions in sheet: {len(df)}")
            
            if df.empty:
                logger.info("No transactions found in sheet")
                return f"📅 Tidak ada transaksi pada {month_display}"
            
            # Filter by specific month and year
            logger.debug(f"Filtering for month: {month_str}")
            monthly = df[df['Date'].dt.strftime('%Y-%m') == month_str]
            logger.info(f"Transactions this month: {len(monthly)}")
            
            if monthly.empty:
                return f"📅 Tidak ada transaksi pada {month_display}"
            
            total = monthly['Price'].sum()
            count = len(monthly)
            
            # Calculate days for the given month, up to the current day if it's the current month
            if year == current_date.year and month == current_date.month:
                days = current_date.day
            else:
                # For past months, use total days in that month
                days = (datetime(year, month % 12 + 1, 1) - datetime(year, month, 1)).days

            avg_per_day = total / days
            
            report = f"{REPORT_MONTHLY_HEADER.format(month=month_display)}\n"
            report += f"⏰ Generated: {current_date.strftime('%d %b %Y, %H:%M:%S')}\n\n"
            
            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n"
            report += f"Rata-rata/hari: {Formatter.format_currency(avg_per_day)}\n\n"
            
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
            
            report += "Ranking Capster:\n"
            for idx, (capster, row) in enumerate(by_capster.iterrows(), 1):
                amount = row['Price']
                count_capster = int(row['Service'])
                report += f"  {idx}. {capster}: {count_capster} layanan ({Formatter.format_currency(amount)})\n"
            
            # Service breakdown
            service_breakdown = monthly.groupby('Service').agg({
                'Price': ['sum', 'count']
            }).sort_values(('Price', 'sum'), ascending=False)
            
            report += "\nBreakdown Layanan:\n"
            for service, row in service_breakdown.iterrows():
                total_service = row[('Price', 'sum')]
                count_service = int(row[('Price', 'count')])
                report += f"  • {service}: {count_service}x ({Formatter.format_currency(total_service)})\n"
            
            # Payment methods breakdown (if exists)
            if 'Payment_Method' in monthly.columns:
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

            # Extract data from the DataFrame for formatting
            total_revenue = profit_data_df.loc['Overall', 'Revenue']
            total_operational_cost = profit_data_df.loc['Overall', 'Operational Cost']
            total_net_profit = profit_data_df.loc['Overall', 'Net Profit']

            revenue_a = profit_data_df.loc['Cabang A', 'Revenue']
            total_costs_a = profit_data_df.loc['Cabang A', 'Operational Cost']
            profit_a = profit_data_df.loc['Cabang A', 'Net Profit']

            revenue_b = profit_data_df.loc['Cabang B', 'Revenue']
            fixed_costs_b = profit_data_df.loc['Cabang B', 'Fixed Cost']
            commission_cost_b = profit_data_df.loc['Cabang B', 'Commission Cost']
            total_costs_b = profit_data_df.loc['Cabang B', 'Operational Cost']
            profit_b = profit_data_df.loc['Cabang B', 'Net Profit']


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

            # Branch A Details
            report += "\n" + "-"*40 + "\n"
            report += f"DETAIL PROFIT CABANG A\n"
            report += "-"*40 + "\n"
            report += f"  - Pendapatan: {Formatter.format_currency(revenue_a)}\n"
            report += f"  - Biaya Operasional (Fixed): {Formatter.format_currency(total_costs_a)}\n"
            profit_emoji_a = "✅" if profit_a >= 0 else "❌"
            report += f"  {profit_emoji_a} Profit Bersih Cabang A: {Formatter.format_currency(profit_a)}\n"

            # Branch B Details
            report += "\n" + "-"*40 + "\n"
            report += f"DETAIL PROFIT CABANG B\n"
            report += "-"*40 + "\n"
            report += f"  - Pendapatan: {Formatter.format_currency(revenue_b)}\n"
            report += "  - Biaya Operasional:\n"
            report += f"    - Fixed: {Formatter.format_currency(fixed_costs_b)}\n"
            report += f"    - Komisi: {Formatter.format_currency(commission_cost_b)}\n"
            report += f"    - Total Biaya: {Formatter.format_currency(total_costs_b)}\n"
            profit_emoji_b = "✅" if profit_b >= 0 else "❌"
            report += f"  {profit_emoji_b} **Profit Bersih Cabang B:** {Formatter.format_currency(profit_b)}\n"
            
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
            # Get all transactions
            df = self._get_or_fetch_transactions()
            
            # Filter for the specific month and year
            month_str = f"{year:04d}-{month:02d}"
            monthly_df = df[df['Date'].dt.strftime('%Y-%m') == month_str]

            if monthly_df.empty or 'Branch' not in monthly_df.columns:
                logger.info(f"No transactions or 'Branch' column missing for {month_str}. Returning empty DataFrame.")
                return pd.DataFrame()

            # Prepare results dictionary
            results = {}

            # --- Calculations for Branch A ---
            branch_a_df = monthly_df[monthly_df['Branch'] == 'Cabang A']
            revenue_a = branch_a_df['Price'].sum()
            costs_a_config = BRANCHES['cabang_a']['oprational_cost']
            total_fixed_costs_a = sum(costs_a_config.values())
            profit_a = revenue_a - total_fixed_costs_a
            
            results['Cabang A'] = {
                'Revenue': revenue_a,
                'Fixed Cost': total_fixed_costs_a,
                'Commission Cost': 0, # Branch A doesn't seem to have commission based on the profit report
                'Operational Cost': total_fixed_costs_a,
                'Net Profit': profit_a
            }

            # --- Calculations for Branch B ---
            branch_b_df = monthly_df[monthly_df['Branch'] == 'Cabang B']
            revenue_b = branch_b_df['Price'].sum()
            costs_b_config = BRANCHES['cabang_b']['oprational_cost']
            fixed_costs_b = sum(costs_b_config.values())
            commission_cost_b = revenue_b * OPRATIONAL_CONFIG['commision_rate']
            total_costs_b = fixed_costs_b + commission_cost_b
            profit_b = revenue_b - total_costs_b

            results['Cabang B'] = {
                'Revenue': revenue_b,
                'Fixed Cost': fixed_costs_b,
                'Commission Cost': commission_cost_b,
                'Operational Cost': total_costs_b,
                'Net Profit': profit_b
            }
            
            # --- Overall Totals ---
            total_revenue_overall = revenue_a + revenue_b
            total_operational_cost_overall = total_fixed_costs_a + total_costs_b # Total_costs_b already includes commission
            total_net_profit_overall = total_revenue_overall - total_operational_cost_overall

            results['Overall'] = {
                'Revenue': total_revenue_overall,
                'Fixed Cost': total_fixed_costs_a + fixed_costs_b, # Sum of fixed costs
                'Commission Cost': commission_cost_b, # Only Branch B has commission
                'Operational Cost': total_operational_cost_overall,
                'Net Profit': total_net_profit_overall
            }
            
            # Convert results to DataFrame
            profit_df = pd.DataFrame.from_dict(results, orient='index')
            profit_df.index.name = 'Category'
            
            return profit_df

        except Exception as e:
            logger.error(f"Failed to generate monthly profit DataFrame for {month}/{year}: {e}", exc_info=True)
            return pd.DataFrame()

    """""
    ## 🎯 **Contoh Output Laporan Mingguan Baru**

    ### **Sebelum (7 hari mundur dari hari ini):**
    ```
    📈 LAPORAN MINGGUAN (7 Hari Terakhir)
    ⏰ Generated: 10:30:00

    Total Transaksi: 42
    Total Pendapatan: Rp 1,500,000
    Rata-rata/hari: Rp 214,285
    ...
    ```

    ### **Sesudah (Senin-Minggu minggu ini):**
    ```
    📈 LAPORAN MINGGUAN (7 Hari Terakhir)
    📅 Periode: 13 Jan - 19 Jan 2026
    ⏰ Generated: 10:30:00

    Total Transaksi: 38
    Total Pendapatan: Rp 1,350,000
    Hari Operasional: 6 hari
    Rata-rata/hari: Rp 225,000

    Per Cabang:
    🏢 Cabang A: 20 transaksi (Rp 700,000)
    🏢 Cabang B: 18 transaksi (Rp 650,000)

    Layanan Terpopuler:
    1. ✂️ Potong Rambut: 25x
    2. 💇 Potong + Cuci: 8x
    3. 🎨 Highlights: 5x

    Top Caster:
    1. John: 15 layanan (Rp 500,000)
    2. Jane: 12 layanan (Rp 450,000)
    3. Mike: 11 layanan (Rp 400,000)

    Per Hari:
    📅 Senin, 13 Jan: 5 transaksi (Rp 175,000)
    📅 Selasa, 14 Jan: 8 transaksi (Rp 280,000)
    📅 Rabu, 15 Jan: 6 transaksi (Rp 210,000)
    📅 Kamis, 16 Jan: 7 transaksi (Rp 245,000)
    📅 Jumat, 17 Jan: 9 transaksi (Rp 315,000)
    📅 Sabtu, 18 Jan: 3 transaksi (Rp 125,000)
    """""
    #SERVICE REPORT HANDLER CAPSTER
    def generate_daily_report_capster(self, user) -> str:
        """Generate daily report for capster"""
        try:
            date = datetime.now()
            df = self.sheets.get_transactions_by_date(date)
            
            # Filter by capster
            df_capster = df[df['Capster'] == user]
            if df_capster.empty:
                return f"📊 Tidak ada transaksi untuk {user} pada {Formatter.format_date(date)}"
            
            total = df_capster['Price'].sum()
            count = len(df_capster)
            
            report = f"{REPORT_DAILY_HEADERS_CAPSTER.format(date=Formatter.format_date(date), username=user)}\n\n"
            report += f"Capster: {user}\n"
            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n\n"
            
            # Top services
            top_services = df_capster['Service'].value_counts().head(3)
            if not top_services.empty:
                report += "Layanan Terpopuler:\n"
                for service, count in top_services.items():
                    report += f"  • {service}: {count}x\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate daily report for capster: {e}")
            return "❌ Gagal membuat laporan harian untuk capster"
    
    def generate_weekly_report_capster(self, user) -> str:
        """Generate weekly report (Monday to Sunday of current week)"""
        logger.info("Generating weekly report")
        
        try:
            # Get current week range (Monday to Sunday)
            monday, sunday = self._get_week_range()
            
            logger.info(f"Fetching transactions from {monday} to {sunday}")
            df = self.sheets.get_transactions_by_range(monday, sunday)
            logger.info(f"Fetched {len(df)} transactions")
            
            if df.empty:
                logger.info("No transactions this week")
                week_str = f"{monday.strftime('%d %b')} - {sunday.strftime('%d %b %Y')}"
                return f"📈 Tidak ada transaksi minggu ini\n({week_str})"
            
            df_capster = df[df['Capster'] == user]
            total = df_capster['Price'].sum()
            count = len(df_capster)
            
            # Calculate days with transactions
            unique_days = df_capster['Date'].dt.date.nunique()
            avg_per_day = total / unique_days if unique_days > 0 else 0
            
            # Week info
            week_str = f"{monday.strftime('%d %b')} - {sunday.strftime('%d %b %Y')}"
            now = datetime.now()
            
            report = f"{REPORT_WEEKLY_HEADER}\n"
            report += f"📅 Periode: {week_str}\n"
            report += f"⏰ Generated: {now.strftime('%H:%M:%S')}\n\n"
            
            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n"
            report += f"Hari Operasional: {unique_days} hari\n"
            report += f"Rata-rata/hari: {Formatter.format_currency(avg_per_day)}\n\n"
            
            # Per branch breakdown (if exists)
            if 'Branch' in df_capster.columns:
                by_branch = df.groupby('Branch')['Price'].agg(['sum', 'count']).sort_values('sum', ascending=False)
                report += "Per Cabang:\n"
                for branch, row in by_branch.iterrows():
                    count_branch = int(row['count'])
                    sum_branch = row['sum']
                    report += f"  🏢 {branch}: {count_branch} transaksi ({Formatter.format_currency(sum_branch)})\n"
                report += "\n"
            
            # Top services
            top_services = df_capster['Service'].value_counts().head(5)
            report += "Layanan Terpopuler:\n"
            for idx, (service, count) in enumerate(top_services.items(), 1):
                report += f"  {idx}. {service}: {count}x\n"
            
            
            # Daily breakdown
            daily_totals = df_capster.groupby(df_capster['Date'].dt.date)['Price'].agg(['sum', 'count'])
            report += "\nPer Hari:\n"
            for date, row in daily_totals.iterrows():
                day_name = pd.Timestamp(date).strftime('%A')  # Monday, Tuesday, etc
                day_name_id = self._translate_day(day_name)  # Senin, Selasa, etc
                count_day = int(row['count'])
                sum_day = row['sum']
                report += f"  📅 {day_name_id}, {pd.Timestamp(date).strftime('%d %b')}: {count_day} transaksi ({Formatter.format_currency(sum_day)})\n"
            
            logger.info("Weekly report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate weekly report: {e}", exc_info=True)
            return f"❌ Gagal membuat laporan mingguan: {str(e)}"
        

    def generate_monthly_report_capster(self, user) -> str:
        """Generate monthly report for capster"""
        try:
            now = datetime.now()
            month_str = now.strftime('%Y-%m')
            
            df = self._get_or_fetch_transactions()
            
            if df.empty:
                return "📅 Tidak ada transaksi bulan ini"
            
            # Filter by capster
            df_capster = df[df['Capster'] == user]
            if df_capster.empty:
                return f"📅 Tidak ada transaksi untuk {user} bulan ini"
            
            total = df_capster['Price'].sum()
            count = len(df_capster)
            days = now.day
            avg_per_day = total / days
            
            report = f"{REPORT_MONTHLY_HEADERS_CAPSTER.format(month=month_str, username=user)}\n\n"
            report += f"Capster: {user}\n"
            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n" 
            report += f"Rata-rata/hari: {Formatter.format_currency(avg_per_day)}\n\n"
            return report
        
        except Exception as e:
            logger.error(f"Failed to generate monthly report for capster: {e}")
            return "❌ Gagal membuat laporan bulanan untuk capster"   