"""Telegram bot — admin reports only.

Re-export entry points dari bot.bot agar bisa:
    from bot import run, build_app
"""
from bot.bot import build_app, run

__all__ = ['build_app', 'run']
