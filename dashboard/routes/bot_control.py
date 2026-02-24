"""Bot on/off control — Flask routes."""
from datetime import datetime

from flask import Blueprint, jsonify, redirect, url_for, flash, request

from dashboard.auth import login_required
from app.bot_manager import BotManager

bot_control_bp = Blueprint('bot_control', __name__)


@bot_control_bp.route('/bot/status')
@login_required
def bot_status():
    """JSON endpoint — dipolling oleh navbar setiap beberapa detik."""
    mgr = BotManager()
    uptime = None
    if mgr.started_at:
        delta = datetime.now() - mgr.started_at
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s   = divmod(rem, 60)
        uptime = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    return jsonify({
        'status':     mgr.status,
        'is_running': mgr.is_running,
        'uptime':     uptime,
        'error':      mgr.error_msg,
    })


@bot_control_bp.route('/bot/start', methods=['POST'])
@login_required
def bot_start():
    mgr = BotManager()
    ok, msg = mgr.start()
    flash(msg, 'success' if ok else 'warning')
    return redirect(request.referrer or url_for('home.index'))


@bot_control_bp.route('/bot/stop', methods=['POST'])
@login_required
def bot_stop():
    mgr = BotManager()
    ok, msg = mgr.stop()
    flash(msg, 'success' if ok else 'warning')
    return redirect(request.referrer or url_for('home.index'))
