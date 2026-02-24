"""
Capster Model
"""
from dataclasses import dataclass, field


@dataclass
class Capster:
    """Capster data"""
    name: str
    telegram_id: int
    alias: str = ''  # Nama Telegram / nama di transaksi lama
    employment_type: str = 'mitra'  # 'mitra' atau 'tetap'
    commission_rate: float = 0.5    # 0.5 = 50% (hanya berlaku untuk mitra)
    monthly_salary: int = 0         # Gaji bulanan (hanya berlaku untuk tetap)
    branch_id: str = ''             # Branch tempat bekerja (untuk perhitungan profit)

    def to_row(self) -> list:
        """Convert to Google Sheets row."""
        return [self.name, self.telegram_id, self.alias,
                self.employment_type, self.commission_rate,
                self.monthly_salary, self.branch_id]

    def all_names(self) -> list:
        """Return all known names (for query matching)."""
        names = [self.name]
        if self.alias and self.alias.lower() != self.name.lower():
            names.append(self.alias)
        return names
