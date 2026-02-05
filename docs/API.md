# 📖 API Documentation

## Services

### SheetsService
```python
from app.services.sheets_service import SheetsService

sheets = SheetsService()

# Add transaction
transaction = Transaction(
    capster="John",
    service="Potong Rambut",
    price=35000
)
sheets.add_transaction(transaction)

# Get all transactions
transactions = sheets.get_all_transactions()

# Get transactions by date
from datetime import datetime
df = sheets.get_transactions_by_date(datetime.now())
```

### ReportService
```python
from app.services.report_service import ReportService

reports = ReportService()

# Generate reports
daily = reports.generate_daily_report()
weekly = reports.generate_weekly_report()
monthly = reports.generate_monthly_report()
```

### AuthService
```python
from app.services.auth_service import AuthService

# Check authorization
is_auth = AuthService.is_authorized(user_id)

# Get authorized users
users = AuthService.get_authorized_users()
```

## Models

### Transaction
```python
from app.models.transaction import Transaction
from datetime import datetime

trans = Transaction(
    capster="Jane",
    service="Styling",
    price=50000,
    date=datetime.now()
)

# Convert to dict
data = trans.to_dict()
```

## Utils

### KeyboardBuilder
```python
from app.utils.keyboards import KeyboardBuilder

# Main menu
keyboard = KeyboardBuilder.main_menu()

# Service menu
keyboard = KeyboardBuilder.service_menu()

# Back button
keyboard = KeyboardBuilder.back_button()
```

### Formatter
```python
from app.utils.formatters import Formatter

# Format currency
text = Formatter.format_currency(35000)  # "Rp 35,000"

# Format date
text = Formatter.format_date(datetime.now())
```