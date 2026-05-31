"""Simple session-based auth for dashboard."""
import os
from functools import wraps
from flask import session, redirect, url_for
from werkzeug.security import check_password_hash

DASHBOARD_PASSWORD_HASH = os.getenv('DASHBOARD_PASSWORD_HASH')
if not DASHBOARD_PASSWORD_HASH:
    raise RuntimeError(
        "DASHBOARD_PASSWORD_HASH belum diset di .env. "
        "Generate dengan: python -c \"from werkzeug.security import generate_password_hash; "
        "print(generate_password_hash('PASSWORD_BARU'))\""
    )


def check_dashboard_password(password: str) -> bool:
    """Constant-time compare hash di env dengan input user."""
    return check_password_hash(DASHBOARD_PASSWORD_HASH, password or '')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('home.login'))
        return f(*args, **kwargs)
    return decorated
