"""
Query Model
"""
from datetime import datetime
from typing import Dict, Optional, List

VALID_REPORT_TYPES = [
    'revenue', 'transaction_count', 'capster_ranking', 'branch_comparison',
    'service_popularity', 'profit', 'daily_summary', 'weekly_summary',
    'monthly_summary', 'general'
]

VALID_TIMEFRAMES = [
    'hari ini', 'kemarin', 'minggu ini', 'minggu lalu',
    'bulan ini', 'bulan lalu', '3 bulan terakhir'
]

class QueryResult:
    """
    Represents the structured result of a parsed natural language query.
    """
    def __init__(self, original_query: str):
        self.original_query: str = original_query
        self.metric: Optional[str] = None
        self.metrics: List[str] = []
        self.timeframe_str: Optional[str] = None
        self.timeframe: Optional[tuple] = None
        self.specific_date: Optional[datetime] = None  # e.g. 2026-01-01 (single date or range start)
        self.date_end: Optional[datetime] = None         # e.g. 2026-01-17 (range end, None if single date)
        self.specific_dates: List[datetime] = []         # multiple discrete dates (non-contiguous)
        self.specific_month: Optional[int] = None       # e.g. 1 for January
        self.specific_year: Optional[int] = None         # e.g. 2026
        self.capsters: List[str] = []
        self.capster_alias_map: Dict[str, List[str]] = {}  # name_lower -> [all known names]
        self.branches: List[str] = []
        self.report_type: Optional[str] = None
        self.sort_by: Optional[str] = None
        self.sort_order: str = 'desc'
        self.limit: int = 10
        self.is_valid_query: bool = True

    def is_valid(self) -> bool:
        """
        Check if the query is valid enough to proceed.
        Valid if at least a metric, report type, timeframe, or specific date is found.
        """
        return (self.metric is not None
                or self.report_type is not None
                or self.timeframe_str is not None
                or self.specific_date is not None
                or self.date_end is not None
                or len(self.specific_dates) > 0
                or self.specific_month is not None
                or len(self.metrics) > 0)

    def __str__(self) -> str:
        parts = [
            f"QueryResult(query='{self.original_query}'",
            f"report_type='{self.report_type}', metric='{self.metric}'",
            f"metrics={self.metrics}, timeframe='{self.timeframe_str}'",
        ]
        if self.specific_date:
            parts.append(f"specific_date='{self.specific_date.strftime('%Y-%m-%d')}'")
        if self.date_end:
            parts.append(f"date_end='{self.date_end.strftime('%Y-%m-%d')}'")
        if self.specific_dates:
            dates_str = ', '.join(d.strftime('%Y-%m-%d') for d in self.specific_dates)
            parts.append(f"specific_dates=[{dates_str}]")
        if self.specific_month:
            parts.append(f"specific_month={self.specific_month}, specific_year={self.specific_year}")
        parts.append(f"capsters={self.capsters}, branches={self.branches}")
        parts.append(f"sort_by='{self.sort_by}', limit={self.limit})")
        return ", ".join(parts)
