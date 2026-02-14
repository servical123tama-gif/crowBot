"""
Query Parser Service - Delegates to Gemini AI with keyword fallback
"""
import re
import logging
from datetime import datetime
from typing import List, Optional, Tuple, Union
from app.models.query import QueryResult
from app.config.constants import BRANCHES, MONTHS_ID_REV

logger = logging.getLogger(__name__)


class QueryParserService:
    """
    Parses natural language queries using Gemini AI with keyword-based fallback.
    """

    def __init__(self, capster_list: List[str], gemini_service=None, capster_alias_map: dict = None):
        self._capster_list = capster_list
        self._capster_list_lower = [name.lower() for name in capster_list]
        self._capster_alias_map = capster_alias_map or {}
        self._branch_list = [branch['name'] for branch_id, branch in BRANCHES.items()]
        self._branch_list_lower = [name.lower() for name in self._branch_list]
        self._gemini_service = gemini_service

        # Branch aliases for keyword fallback
        self._branch_aliases = {
            'denailla': 'Cabang Denailla',
            'mojosari': 'Cabang Denailla',
            'cabang a': 'Cabang Denailla',
            'sumput': 'Cabang Sumput',
            'cabang b': 'Cabang Sumput',
        }

    def update_capster_list(self, capster_list: List[str]):
        """Update capster list dynamically."""
        self._capster_list = capster_list
        self._capster_list_lower = [name.lower() for name in capster_list]

    async def parse_query(self, user_query: str) -> QueryResult:
        """
        Parse user query: try Gemini first, fallback to keyword matching.
        """
        # Try Gemini AI first
        if self._gemini_service and self._gemini_service.is_available:
            try:
                result = await self._gemini_service.parse_query_intent(
                    user_query, self._capster_list, self._branch_list
                )
                if result and result.is_valid():
                    logger.info("Query parsed successfully via Gemini AI")
                    result.capster_alias_map = self._capster_alias_map
                    return result
                logger.warning("Gemini returned invalid result, falling back to keywords")
            except Exception as e:
                logger.error(f"Gemini parsing failed, falling back to keywords: {e}")

        # Fallback to keyword matching
        result = self._keyword_fallback(user_query)
        result.capster_alias_map = self._capster_alias_map
        return result

    def _keyword_fallback(self, user_query: str) -> QueryResult:
        """Enhanced keyword-based parsing as fallback."""
        query_result = QueryResult(original_query=user_query)
        lower_query = user_query.lower()

        # --- REPORT TYPE & METRICS ---
        if any(kw in lower_query for kw in ['ranking', 'terbaik', 'top capster', 'capster terbaik', 'peringkat']):
            query_result.report_type = 'capster_ranking'
            query_result.metrics = ['revenue', 'transaction_count']
        elif any(kw in lower_query for kw in ['banding', 'perbandingan', 'compare', 'vs cabang']):
            query_result.report_type = 'branch_comparison'
            query_result.metrics = ['revenue', 'transaction_count']
        elif any(kw in lower_query for kw in ['layanan populer', 'service terpopuler', 'paling laku', 'terlaris']):
            query_result.report_type = 'service_popularity'
            query_result.metrics = ['transaction_count']
        elif any(kw in lower_query for kw in ['laba', 'rugi', 'profit', 'keuntungan', 'margin']):
            query_result.report_type = 'profit'
            query_result.metric = 'profit'
            query_result.metrics = ['revenue', 'profit']
        elif any(kw in lower_query for kw in ['pendapatan', 'revenue', 'omzet', 'omset', 'pemasukan', 'income']):
            query_result.report_type = 'revenue'
            query_result.metric = 'pendapatan'
            query_result.metrics = ['revenue']
        elif any(kw in lower_query for kw in ['transaksi', 'transaction', 'jumlah']):
            query_result.report_type = 'transaction_count'
            query_result.metric = 'transaksi'
            query_result.metrics = ['transaction_count']
        elif any(kw in lower_query for kw in ['laporan harian', 'ringkasan harian', 'daily']):
            query_result.report_type = 'daily_summary'
            query_result.metrics = ['revenue', 'transaction_count']
        elif any(kw in lower_query for kw in ['laporan mingguan', 'ringkasan mingguan', 'weekly']):
            query_result.report_type = 'weekly_summary'
            query_result.metrics = ['revenue', 'transaction_count']
        elif any(kw in lower_query for kw in ['laporan bulanan', 'ringkasan bulanan', 'monthly', 'laporan bulan']):
            query_result.report_type = 'monthly_summary'
            query_result.metrics = ['revenue', 'transaction_count']
        else:
            # Default: general query
            query_result.report_type = 'general'
            query_result.metrics = ['revenue', 'transaction_count']

        # --- TIMEFRAME ---
        # Priority: multiple dates > date range > single date > specific month > relative keyword > default
        multi_dates = self._parse_multiple_dates(lower_query)
        date_range = None if multi_dates else self._parse_date_range(lower_query)

        if multi_dates:
            query_result.specific_dates = multi_dates
            dates_display = ', '.join(d.strftime('%d %B %Y') for d in multi_dates)
            query_result.timeframe_str = f"tanggal {dates_display}"
        elif date_range:
            query_result.specific_date = date_range[0]
            query_result.date_end = date_range[1]
            query_result.timeframe_str = (
                f"{date_range[0].strftime('%d %B %Y')} - {date_range[1].strftime('%d %B %Y')}"
            )
        else:
            specific_date = self._parse_specific_date(lower_query)
            specific_month = self._parse_specific_month(lower_query)

            if specific_date:
                query_result.specific_date = specific_date
                query_result.timeframe_str = f"tanggal {specific_date.strftime('%d %B %Y')}"
            elif specific_month:
                month_num, year_num = specific_month
                query_result.specific_month = month_num
                query_result.specific_year = year_num
                from app.config.constants import MONTHS_ID
                month_name = MONTHS_ID.get(month_num, str(month_num))
                query_result.timeframe_str = f"{month_name} {year_num}"
            elif 'hari ini' in lower_query:
                query_result.timeframe_str = 'hari ini'
            elif 'kemarin' in lower_query:
                query_result.timeframe_str = 'kemarin'
            elif 'minggu lalu' in lower_query:
                query_result.timeframe_str = 'minggu lalu'
            elif 'minggu ini' in lower_query:
                query_result.timeframe_str = 'minggu ini'
            elif 'bulan lalu' in lower_query:
                query_result.timeframe_str = 'bulan lalu'
            elif 'bulan ini' in lower_query:
                query_result.timeframe_str = 'bulan ini'
            elif '3 bulan' in lower_query or 'tiga bulan' in lower_query:
                query_result.timeframe_str = '3 bulan terakhir'
            else:
                query_result.timeframe_str = 'bulan ini'

        # --- ENTITIES: Capsters ---
        for i, capster_lower in enumerate(self._capster_list_lower):
            if capster_lower in lower_query:
                query_result.capsters.append(self._capster_list[i])

        # --- ENTITIES: Branches (with aliases) ---
        for alias, branch_name in self._branch_aliases.items():
            if alias in lower_query and branch_name not in query_result.branches:
                query_result.branches.append(branch_name)

        for i, branch_lower in enumerate(self._branch_list_lower):
            if branch_lower in lower_query and self._branch_list[i] not in query_result.branches:
                query_result.branches.append(self._branch_list[i])

        # Mark validity
        query_result.is_valid_query = query_result.is_valid()

        logger.info(f"Keyword fallback parsed query: {query_result}")
        return query_result

    def _get_month_map(self) -> dict:
        """Build month name to number mapping including abbreviations."""
        month_map = {}
        for name, num in MONTHS_ID_REV.items():
            month_map[name.lower()] = num
        month_map.update({
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mei': 5, 'jun': 6,
            'jul': 7, 'agu': 8, 'ags': 8, 'aug': 8, 'sep': 9, 'okt': 10, 'oct': 10,
            'nov': 11, 'des': 12, 'dec': 12,
        })
        return month_map

    def _get_month_pattern(self, month_map: dict) -> str:
        """Build regex alternation pattern for month names."""
        return '|'.join(sorted(month_map.keys(), key=len, reverse=True))

    def _parse_multiple_dates(self, lower_query: str) -> List[datetime]:
        """
        Parse multiple discrete dates separated by commas or 'dan'.
        Supports: "15 januari 2026, 18 januari 2026, 2 feb 2026"
                  "tanggal 1 jan dan 5 jan 2026"
                  "1 feb 2026, 3 feb 2026 dan 7 feb 2026"
        Returns: list of datetime objects (2+ dates), or empty list
        """
        month_map = self._get_month_map()
        month_names = self._get_month_pattern(month_map)

        # Find all date occurrences in the query
        date_pattern = rf'(\d{{1,2}})\s+({month_names})\s*(\d{{4}})?'
        matches = list(re.finditer(date_pattern, lower_query))

        if len(matches) < 2:
            return []

        # Check if dates are separated by commas or 'dan' (not range separators)
        # If a range separator exists between first two dates, it's a range, not multi-date
        range_seps = ['sampai', 'hingga', 's/d', 's.d.', ' sd ', ' - ']
        text_between_first_two = lower_query[matches[0].end():matches[1].start()]
        for sep in range_seps:
            if sep in text_between_first_two:
                return []  # This is a range, not multiple discrete dates

        # Parse all dates
        parsed_dates = []
        last_year = None
        # Process in reverse to propagate year from right to left
        for match in reversed(matches):
            day = int(match.group(1))
            month_str = match.group(2)
            year_str = match.group(3)

            month_num = month_map.get(month_str)
            if not month_num:
                continue

            if year_str:
                year_num = int(year_str)
                last_year = year_num
            elif last_year:
                year_num = last_year
            else:
                year_num = datetime.now().year

            try:
                parsed_dates.append(datetime(year_num, month_num, day))
            except ValueError:
                continue

        if len(parsed_dates) < 2:
            return []

        # Reverse back to original order and sort
        parsed_dates.reverse()
        parsed_dates.sort()
        return parsed_dates

    def _parse_date_range(self, lower_query: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Parse date range from query.
        Supports:
          - "15 januari 2026 sampai 17 januari 2026"
          - "tanggal 1 feb sampai 5 feb 2026"
          - "1 jan 2026 hingga 15 jan 2026"
          - "tgl 1 s/d 5 januari 2026" (same month shorthand)
          - "1 - 5 januari 2026"
        Returns: (start_date, end_date) or None
        """
        month_map = self._get_month_map()
        month_names = self._get_month_pattern(month_map)

        # Separator pattern
        sep = r'\s+(?:sampai|hingga|s/?d|s\.d\.|ke|sd|-)\s+'

        # Pattern 1: full dates on both sides — "15 januari 2026 sampai 17 januari 2026"
        date_part = rf'(?:tanggal|tgl)?\s*(\d{{1,2}})\s+({month_names})\s*(\d{{4}})?'
        pattern_full = rf'{date_part}{sep}{date_part}'
        match = re.search(pattern_full, lower_query)

        if match:
            d1, m1_str, y1_str, d2, m2_str, y2_str = match.groups()
            m1 = month_map.get(m1_str)
            m2 = month_map.get(m2_str)
            if m1 and m2:
                now_year = datetime.now().year
                y1 = int(y1_str) if y1_str else (int(y2_str) if y2_str else now_year)
                y2 = int(y2_str) if y2_str else y1
                try:
                    start = datetime(y1, m1, int(d1))
                    end = datetime(y2, m2, int(d2))
                    if end >= start:
                        return (start, end)
                except ValueError:
                    pass

        # Pattern 2: same month shorthand — "1 s/d 5 januari 2026", "1 - 5 feb"
        pattern_short = rf'(?:tanggal|tgl)?\s*(\d{{1,2}})\s*(?:sampai|hingga|s/?d|s\.d\.|sd|-)\s*(\d{{1,2}})\s+({month_names})\s*(\d{{4}})?'
        match = re.search(pattern_short, lower_query)

        if match:
            d1, d2, m_str, y_str = match.groups()
            m = month_map.get(m_str)
            if m:
                y = int(y_str) if y_str else datetime.now().year
                try:
                    start = datetime(y, m, int(d1))
                    end = datetime(y, m, int(d2))
                    if end >= start:
                        return (start, end)
                except ValueError:
                    pass

        return None

    def _parse_specific_date(self, lower_query: str) -> Optional[datetime]:
        """
        Parse specific date from query.
        Supports: "tanggal 1 januari 2026", "1 januari 2026", "tgl 5 feb 2026",
                  "tanggal 1 jan", "1 feb" (assumes current year)
        """
        month_map = self._get_month_map()
        month_names = self._get_month_pattern(month_map)

        # Pattern: (tanggal|tgl)? <day> <month_name> <year>?
        pattern = rf'(?:tanggal|tgl)?\s*(\d{{1,2}})\s+({month_names})\s*(\d{{4}})?'
        match = re.search(pattern, lower_query)

        if match:
            day = int(match.group(1))
            month_str = match.group(2)
            year_str = match.group(3)

            month_num = month_map.get(month_str)
            if not month_num:
                return None

            year_num = int(year_str) if year_str else datetime.now().year

            try:
                return datetime(year_num, month_num, day)
            except ValueError:
                logger.warning(f"Invalid date: {day}/{month_num}/{year_num}")
                return None

        return None

    def _parse_specific_month(self, lower_query: str) -> Optional[tuple]:
        """
        Parse specific month from query (without specific day).
        Supports: "januari 2026", "bulan januari 2026", "bulan jan",
                  "februari", "maret 2025"
        Returns: (month_num, year_num) or None
        """
        month_map = self._get_month_map()
        month_names = self._get_month_pattern(month_map)

        # Pattern: (bulan)? <month_name> <year>? — but NOT preceded by a digit (that would be a specific date)
        pattern = rf'(?:bulan\s+)?({month_names})\s*(\d{{4}})?'
        match = re.search(pattern, lower_query)

        if match:
            # Check if preceded by a digit (means it's a specific date, not just a month)
            start = match.start()
            before = lower_query[:start].rstrip()
            if before and re.search(r'\d$', before):
                return None  # This is a specific date like "1 januari 2026"

            month_str = match.group(1)
            year_str = match.group(2)

            month_num = month_map.get(month_str)
            if not month_num:
                return None

            year_num = int(year_str) if year_str else datetime.now().year

            # Don't match if it's a relative timeframe keyword
            # e.g., "bulan ini", "bulan lalu" — these contain month names like "ini"/"lalu" not in our map
            # so they won't match, which is correct

            return (month_num, year_num)

        return None
