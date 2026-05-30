"""Public-facing landing page — accessible without login."""
from flask import Blueprint, render_template, request, redirect
from app.db.repository import Repository
from app.config.constants import BRANCHES

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def landing():
    repo = Repository()
    services = repo.get_all_services()
    branches = [
        {
            'id':       bid,
            'name':     cfg.get('name', bid),
            'location': cfg.get('location', ''),
            'short':    cfg.get('short', bid),
        }
        for bid, cfg in BRANCHES.items()
    ]
    return render_template('public.html', services=services, branches=branches)
