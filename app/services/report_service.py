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

class ReportService:
    """Generate reports"""
    
    def __init__(self):
        try:
            logger.info("Initializing ReportService...")
            self.sheets = SheetsService()
           
            self.week_calc = WeekCalculator()  # ← NEW
            logger.info("ReportService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReportService: {e}", exc_info=True)
            raise
    
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
            df = self.sheets.get_transactions_dataframe()
            
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
            
            # Top casters
            
            top_casters = df.groupby('Caster')['Price'].sum().sort_values(ascending=False).head(5)
            report += "Top Caster:\n"
            for idx, (caster, amount) in enumerate(top_casters.items(), 1):
                caster_count = df[df['Caster'] == caster].shape[0]
                report += f"  {idx}. {caster}: {caster_count} layanan ({Formatter.format_currency(amount)})\n"
            
            # Top services
            top_services = df['Service'].value_counts().head(5)
            report += "\nLayanan Terpopuler:\n"
            for idx, (service, count) in enumerate(top_services.items(), 1):
                report += f"  {idx}. {service}: {count}x\n"
            
            # Daily breakdown
            daily_totals = df.groupby(df['Date'].dt.date)['Price'].agg(['sum', 'count'])
            report += "\nPer Hari:\n"
            for date, row in daily_totals.iterrows():
                day_name = pd.Timestamp(date).strftime('%A')
                day_name_id = self._translate_day(day_name)
                count_day = int(row['count'])
                sum_day = row['sum']
                report += f"  📅 {day_name_id}, {pd.Timestamp(date).strftime('%d %b')}: {count_day} transaksi ({Formatter.format_currency(sum_day)})\n"
                # Per capster breakdown for this day
                day_df = df[df['Date'].dt.date == date]
                by_capster = day_df.groupby('Caster')['Price'].agg(['sum', 'count']).sort_values('sum', ascending=False)
                for capster, capster_row in by_capster.iterrows():
                    capster_count = int(capster_row['count'])
                    capster_sum = capster_row['sum']
                    report += f"-{capster}: {capster_count} layanan ({Formatter.format_currency(capster_sum)})\n"
                report += "\n"
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
            
            # Per caster breakdown
            logger.debug("Generating per-caster breakdown...")
            by_caster = df.groupby('Caster')['Price'].agg(['sum', 'count'])
            report += "Per Caster:\n"
            
            for caster, row in by_caster.iterrows():
                count_caster = int(row['count'])
                sum_caster = row['sum']
                report += f"  ✂️ {caster}: {count_caster} layanan ({Formatter.format_currency(sum_caster)})\n"
            
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
            
            # Top casters
            top_casters = df.groupby('Caster')['Price'].sum().sort_values(ascending=False).head(5)
            report += "\nTop Caster:\n"
            for idx, (caster, amount) in enumerate(top_casters.items(), 1):
                # Count transactions per caster
                caster_count = df[df['Caster'] == caster].shape[0]
                report += f"  {idx}. {caster}: {caster_count} layanan ({Formatter.format_currency(amount)})\n"
            
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
    
    def generate_monthly_report(self) -> str:
        """Generate monthly report"""
        logger.info("Generating monthly report")
        
        try:
            now = datetime.now()
            month_str = now.strftime('%Y-%m')
            month_display = now.strftime('%B %Y')
            
            logger.debug("Fetching all transactions...")
            df = self.sheets.get_transactions_dataframe()
            logger.info(f"Total transactions in sheet: {len(df)}")
            
            if df.empty:
                logger.info("No transactions found in sheet")
                return "📅 Tidak ada transaksi bulan ini"
            
            # Filter by current month
            logger.debug(f"Filtering for month: {month_str}")
            monthly = df[df['Date'].dt.strftime('%Y-%m') == month_str]
            logger.info(f"Transactions this month: {len(monthly)}")
            
            if monthly.empty:
                return f"📅 Tidak ada transaksi pada {month_display}"
            
            total = monthly['Price'].sum()
            count = len(monthly)
            days = now.day
            avg_per_day = total / days
            
            report = f"{REPORT_MONTHLY_HEADER.format(month=month_display)}\n"
            report += f"⏰ Generated: {now.strftime('%d %b %Y, %H:%M:%S')}\n\n"
            
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
            
            # Ranking caster
            by_caster = monthly.groupby('Caster').agg({
                'Price': 'sum',
                'Service': 'count'
            }).sort_values('Price', ascending=False)
            
            report += "Ranking Caster:\n"
            for idx, (caster, row) in enumerate(by_caster.iterrows(), 1):
                amount = row['Price']
                count_caster = int(row['Service'])
                report += f"  {idx}. {caster}: {count_caster} layanan ({Formatter.format_currency(amount)})\n"
            
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
            
            logger.info("Monthly report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate monthly report: {e}", exc_info=True)
            return f"❌ Gagal membuat laporan bulanan: {str(e)}"
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
            
            if df.empty:
                return f"📊 Tidak ada transaksi pada {Formatter.format_date(date)}"
            
            # Filter by caster
            df_caster = df[df['Caster'] == user]
            if df_caster.empty:
                return f"📊 Tidak ada transaksi untuk {user} pada {Formatter.format_date(date)}"
            
            total = df_caster['Price'].sum()
            count = len(df_caster)
            
            report = f"{REPORT_DAILY_HEADERS_CAPSTER.format(date=Formatter.format_date(date), username=user)}\n\n"
            report += f"Caster: {user}\n"
            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n\n"
            
            # Top services
            top_services = df_caster['Service'].value_counts().head(3)
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
            
            df_capster = df[df['Caster'] == user]
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
            
            df = self.sheets.get_transactions_dataframe()
            
            if df.empty:
                return "📅 Tidak ada transaksi bulan ini"
            
            # Filter by caster
            df_caster = df[df['Caster'] == user]
            if df_caster.empty:
                return f"📅 Tidak ada transaksi untuk {user} bulan ini"
            
            total = df_caster['Price'].sum()
            count = len(df_caster)
            days = now.day
            avg_per_day = total / days
            
            report = f"{REPORT_MONTHLY_HEADERS_CAPSTER.format(month=month_str, username=user)}\n\n"
            report += f"Caster: {user}\n"
            report += f"Total Transaksi: {count}\n"
            report += f"Total Pendapatan: {Formatter.format_currency(total)}\n" 
            report += f"Rata-rata/hari: {Formatter.format_currency(avg_per_day)}\n\n"
            return report
        
        except Exception as e:
            logger.error(f"Failed to generate monthly report for capster: {e}")
            return "❌ Gagal membuat laporan bulanan untuk capster"   