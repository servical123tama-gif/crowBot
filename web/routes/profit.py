"""Profit Report page."""
from datetime import datetime

from flask import Blueprint, render_template, request

from web.auth import login_required
from app.db.repository import Repository
from app.services.reports import calc_profit

profit_bp = Blueprint('profit', __name__)


@profit_bp.route('/profit')
@login_required
def profit():
    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))

    db   = Repository()
    data = calc_profit(db, year, month)

    # Month selector options
    months = [
        {'value': m, 'label': datetime(2000, m, 1).strftime('%B')}
        for m in range(1, 13)
    ]
    years = list(range(2024, now.year + 1))

    return render_template(
        'profit.html',
        data=data,
        year=year,
        month=month,
        month_name=datetime(year, month, 1).strftime('%B %Y'),
        months=months,
        years=years,
        active_page='profit',
    )
