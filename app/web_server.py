"""
Web Server for Health Check (Render.com)
"""
from flask import Flask
from threading import Thread
import logging
import os

logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    """Homepage endpoint"""
    return """
    <html>
        <head><title>Barbershop Bot</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>🤖 Barbershop Bot is Running!</h1>
            <p>CrowBot barbershop</p>
            <p><a href="/health">Check Health Status</a></p>
        </body>
    </html>
    """, 200

@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
    return {
        "status": "ok",
        "bot": "online",
        "service": "barbershop-bot"
    }, 200

def run():
    """Run Flask web server"""
    try:
        # Port dari environment variable (Render provide ini)
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Web server error: {e}")

def keep_alive():
    """Start web server in background thread"""
    import os
    t = Thread(target=run, daemon=True)
    t.start()
    logger.info(f"✅ Health check server started on port {os.environ.get('PORT', 8080)}")