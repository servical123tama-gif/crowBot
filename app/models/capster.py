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

    def to_row(self) -> list:
        """Convert to Google Sheets row."""
        return [self.name, self.telegram_id, self.alias]

    def all_names(self) -> list:
        """Return all known names (for query matching)."""
        names = [self.name]
        if self.alias and self.alias.lower() != self.name.lower():
            names.append(self.alias)
        return names
