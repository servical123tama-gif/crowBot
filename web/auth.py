"""Simple session-based auth for dashboard."""
import os
from functools import wraps
from flask import session, redirect, url_for

DASHBOARD_PASSWORD = os.getenv('DASHBOARD_PASSWORD')
if not DASHBOARD_PASSWORD:
    raise RuntimeError(
        "DASHBOARD_PASSWORD belum diset di .env. "
        "Set password admin minimal 8 karakter, jangan pakai default lama."
    )


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('home.login'))
        return f(*args, **kwargs)
    return decorated
