# 🚀 Deployment Guide

## Option 1: Local/VPS (Recommended untuk Kontrol Penuh)

### Linux/Ubuntu VPS
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3 python3-pip python3-venv -y

# Clone project
git clone <your-repo>
cd barbershop-bot

# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup .env dan credentials.json

# Test run
python run.py

# Setup sebagai service (systemd)
sudo nano /etc/systemd/system/barbershop-bot.service
```

**Service file:**
```ini
[Unit]
Description=Barbershop Telegram Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/barbershop-bot
Environment="PATH=/path/to/barbershop-bot/venv/bin"
ExecStart=/path/to/barbershop-bot/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
# Enable dan start service
sudo systemctl daemon-reload
sudo systemctl enable barbershop-bot
sudo systemctl start barbershop-bot
sudo systemctl status barbershop-bot
```

## Option 2: Replit (Gratis, Simple)

1. Buka [Replit.com](https://replit.com)
2. Create New Repl → Import from GitHub
3. Upload semua file
4. Setup Secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `GOOGLE_SHEET_ID`
   - `AUTHORIZED_CASTERS`
5. Upload `credentials.json` via Files
6. Klik Run

**Keep alive dengan UptimeRobot:**
- Daftar di uptimerobot.com
- Add Monitor → HTTP(s)
- URL: Your replit URL
- Interval: 5 minutes

## Option 3: PythonAnywhere (Gratis, Stabil)

1. Daftar di [PythonAnywhere.com](https://pythonanywhere.com)
2. Upload files via Files tab
3. Open Bash console
4. Setup virtual environment
5. Install dependencies
6. Create "Always On" task

## Option 4: Docker
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run.py"]
```
```bash
# Build dan run
docker build -t barbershop-bot .
docker run -d --name barbershop-bot \
  --env-file .env \
  -v $(pwd)/credentials.json:/app/credentials.json \
  barbershop-bot
```

## Monitoring
```bash
# Cek logs
tail -f logs/bot.log

# Systemd logs
sudo journalctl -u barbershop-bot -f
```

## Backup Otomatis

Setup cron job:
```bash
crontab -e

# Backup setiap hari jam 2 pagi
0 2 * * * cd /path/to/barbershop-bot && /path/to/venv/bin/python scripts/backup.py
```