"""Text formatters for Telegram messages (MarkdownV2-safe)."""
from datetime import datetime


_MD2_SPECIALS = r'_*[]()~`>#+-=|{}.!\\'


def md2_escape(text: str) -> str:
    """Escape characters with special meaning in MarkdownV2."""
    if text is None:
        return ''
    out = []
    for ch in str(text):
        if ch in _MD2_SPECIALS:
            out.append('\\' + ch)
        else:
            out.append(ch)
    return ''.join(out)


def fmt_idr(amount) -> str:
    """Format integer as Indonesian Rupiah: 25000 -> 'Rp 25.000'."""
    try:
        n = int(amount or 0)
    except (ValueError, TypeError):
        n = 0
    return f"Rp {n:,}".replace(',', '.')


def fmt_date(dt: datetime, fmt: str = '%d-%m-%Y') -> str:
    return dt.strftime(fmt) if dt else ''


MONTHS_ID = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember',
}


def fmt_month_id(year: int, month: int) -> str:
    return f"{MONTHS_ID.get(month, month)} {year}"
