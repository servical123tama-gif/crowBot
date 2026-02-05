"""
Report Model
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

@dataclass
class ReportSummary:
    """Report summary data model"""
    total_transactions: int
    total_revenue: float
    period: str
    start_date: datetime
    end_date: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_transactions': self.total_transactions,
            'total_revenue': self.total_revenue,
            'period': self.period,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }

@dataclass
class CapsterPerformance:
    """Capster performance data"""
    name: str
    total_services: int
    total_revenue: float
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'total_services': self.total_services,
            'total_revenue': self.total_revenue,
            'rank': self.rank
        }