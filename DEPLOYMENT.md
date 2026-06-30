# Deploy Crypto Bot to DigitalOcean

## 1. Create a DigitalOcean Droplet

1. Go to https://www.digitalocean.com/
2. Click **Create** → **Droplets**
3. Choose:
   - **Image**: Ubuntu 22.04 LTS
   - **Size**: $6/month (1 GB RAM, 1 vCPU) — plenty for this bot
   - **Region**: Any (pick closest to you or Binance servers)
   - **Auth**: Add your SSH key or set a password
4. Click **Create Droplet**
5. Wait ~1 minute for the droplet to boot, then note its IP address

## 2. SSH into the Droplet

```bash
ssh root@<your_droplet_ip>
```

If using password auth:
```bash
ssh -o StrictHostKeyChecking=no root@<your_droplet_ip>
```

## 3. Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python and tools
apt install -y python3 python3-pip python3-venv git curl wget

# Install systemd service manager (already included, but verify)
apt install -y systemd
```

## 4. Clone or Upload Your Bot

```bash
# Option A: pull from GitHub on the VPS
cd /opt
git clone https://github.com/<your-username>/<your-repo>.git crypto_bot
cd /opt/crypto_bot

# If your code is not on GitHub yet, do this on your local machine first:
# cd /Users/kavishanyadeesha/crypto_bot
# git init
# git add .
# git commit -m "Initial crypto bot upload"
# git branch -M main
# git remote add origin https://github.com/<your-username>/<your-repo>.git
# git push -u origin main

# Option B: upload your local files directly to the VPS
# Run this from your local machine, not from inside the VPS.
# First create the destination folder on the VPS:
ssh root@<your_droplet_ip> "mkdir -p /opt/crypto_bot"

# Then copy the project files:
scp -r /Users/kavishanyadeesha/crypto_bot/* root@<your_droplet_ip>:/opt/crypto_bot/

# If you prefer rsync instead of scp:
# rsync -av --exclude 'venv' --exclude '.git' /Users/kavishanyadeesha/crypto_bot/ root@<your_droplet_ip>:/opt/crypto_bot/
```

## 5. Set Up Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If you uploaded files directly to the VPS, make sure you are already inside `/opt/crypto_bot` before running the commands above.

If you see `status=203/EXEC` or `No such file or directory` for `/opt/crypto_bot/venv/bin/python`, run:

```bash
cd /opt/crypto_bot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
ls -l venv/bin/python
```

## 6. Create `.env` File

```bash
cat > .env << 'EOF'
BINANCE_API_KEY=ERw37zL160TWgdnw8mgK9aZDBKCpLCkxa5DAaLmcXo4xLDq5DvHPy1Qye6zSsZTv
BINANCE_API_SECRET=mq38UV9sitv4JaaOKaaERJUGh1mkQv87JTykrBrMlP0l2kIaDlT4gO4ObKYId3pd

EOF
```

Replace with your actual Binance API keys.

## 7. Create a Systemd Service File

```bash
sudo tee /etc/systemd/system/crypto-bot.service > /dev/null << 'EOF'
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/crypto_bot
Environment="PATH=/opt/crypto_bot/venv/bin"
ExecStart=/opt/crypto_bot/venv/bin/python /opt/crypto_bot/app.py
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
EOF
```

## 8. Enable and Start the Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable to start on boot
sudo systemctl enable crypto-bot

# Start the service
sudo systemctl start crypto-bot

# Check status
sudo systemctl status crypto-bot

# View logs in real-time
sudo journalctl -u crypto-bot -f
```

## 9. Access the Dashboard

Open your browser and go to:
```
http://<your_droplet_ip>:8080
```

## 10. Keeping It Running

### View Logs
```bash
sudo journalctl -u crypto-bot -f
```

### Restart the Bot
```bash
sudo systemctl restart crypto-bot
```

### Stop the Bot
```bash
sudo systemctl stop crypto-bot
```

### Check if Running
```bash
sudo systemctl status crypto-bot
```

## 11. Optional: Set Up Monitoring/Alerts

If the bot crashes, systemd will auto-restart it after 10 seconds.

To monitor the droplet:
1. Go to DigitalOcean dashboard
2. Click your droplet
3. Go to **Monitoring** → Enable monitoring (free)
4. Set up alerts for CPU/memory/disk

## 12. Optional: Auto-Update and Backup

### Pull Latest Code
```bash
cd /opt/crypto_bot
git pull
sudo systemctl restart crypto-bot
```

### Backup Database (trades.db)
```bash
# Weekly backup (add to crontab)
0 0 * * 0 cp /opt/crypto_bot/trades.db /opt/crypto_bot/backups/trades_$(date +%Y%m%d).db
```

## Cost Breakdown

- **Droplet**: $6/month (1 GB, 1 vCPU)
- **Bandwidth**: Included (1 TB/month free)
- **Total**: ~$6/month

Your bot will run 24/7 without you needing to keep your local machine on.

## Troubleshooting

### Bot not starting?
```bash
sudo journalctl -u crypto-bot -n 50  # View last 50 log lines
```

### Port 8080 blocked?
Edit `/etc/systemd/system/crypto-bot.service` and add `ProtectPorts=false`, then reload.

### Need to restart after code changes?
```bash
cd /opt/crypto_bot && git pull
sudo systemctl restart crypto-bot
```

### Service says `/opt/crypto_bot/venv/bin/python: No such file or directory`?
```bash
cd /opt/crypto_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crypto-bot
```

### Check if Flask is listening on port 8080?
```bash
sudo netstat -tlnp | grep 8080
```
