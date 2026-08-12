"""Nomor telepon Indonesia — normalisasi ke format E.164 (628xxx) + display.

Wa.me hanya menerima format internasional tanpa `+`, jadi kita normalize di
input & simpan format bersih. Tampilan tetap boleh pakai `+62 xxx-xxx-xxx`.
"""
import re


def normalize_id_phone(raw: str) -> str:
    """Normalize nomor HP Indonesia ke '628xxxxxxxx' (E.164 tanpa +).

    Handling:
      - `08xxx` → `628xxx`
      - `+628xxx` → `628xxx`
      - `62 857-xxx-xxxx` → `62857xxxxxxx` (strip separator)
      - `895-xxxx` (kurang digit) → dikembalikan apa adanya (tidak dipaksa)
      - Karakter unicode invisible di-strip
      - Empty / None → '' (kosong)
    Return: string bersih. Kalau input tidak valid Indonesia, return sebersih mungkin.
    """
    if not raw:
        return ''
    # Strip semua non-digit (termasuk zero-width, spasi, dash, plus)
    digits = re.sub(r'\D', '', str(raw))
    if not digits:
        return ''
    # 08xxx → 628xxx
    if digits.startswith('0'):
        digits = '62' + digits[1:]
    # 8xxx → 628xxx (kadang user input tanpa 0)
    elif digits.startswith('8') and len(digits) >= 9:
        digits = '62' + digits
    # Kalau sudah 62xxx, biarkan
    # Kalau prefix lain (mis. 1xxx dari US), biarkan — tidak ubah.
    return digits


def display_id_phone(raw: str) -> str:
    """Format tampilan yang gampang dibaca: '+62 857-1234-5678'.

    Kalau input tidak Indonesia atau tidak match, return raw as-is.
    """
    n = normalize_id_phone(raw)
    if not n or not n.startswith('62') or len(n) < 10:
        return raw or ''
    # Split: 62 | XXX | XXXX | rest
    body = n[2:]
    if len(body) <= 3:
        return f'+62 {body}'
    if len(body) <= 7:
        return f'+62 {body[:3]}-{body[3:]}'
    return f'+62 {body[:3]}-{body[3:7]}-{body[7:]}'


def wa_me_url(raw: str) -> str:
    """Return URL wa.me/... atau string kosong kalau nomor invalid."""
    n = normalize_id_phone(raw)
    if not n or len(n) < 9:
        return ''
    return f'https://wa.me/{n}'
