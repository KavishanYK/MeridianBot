# 📚 Quick Server Reference

## 🚀 Getting Your Bot Online (5 minutes)

### 1. Create DigitalOcean Droplet
```bash
# Go to: https://www.digitalocean.com/
# Create Ubuntu 22.04 LTS droplet ($6/month)
# SSH into it
ssh root@<your_droplet_ip>
```

### 2. Run Deployment Script
```bash
# Download and run the auto-deployment script
curl -O https://raw.githubusercontent.com/yourusername/crypto_bot/main/deploy.sh
chmod +x deploy.sh
./deploy.sh
```

### 3. Add Your API Keys
```bash
# Edit .env with your Binance keys
nano /opt/crypto_bot/.env

# Save (Ctrl+X, then Y, then Enter)

# Restart the bot
sudo systemctl restart crypto-bot
```

### 4. Access Your Dashboard
Open in browser:
```
http://your.droplet.ip:8080
```

---

## 🔧 Common Commands

### Check Bot Status
```bash
sudo systemctl status crypto-bot
```

### View Live Logs
```bash
sudo journalctl -u crypto-bot -f
```

### View Last 50 Log Lines
```bash
sudo journalctl -u crypto-bot -n 50
```

### Restart Bot
```bash
sudo systemctl restart crypto-bot
```

### Stop Bot
```bash
sudo systemctl stop crypto-bot
```

### Start Bot
```bash
sudo systemctl start crypto-bot
```

### Download Trade Database (trades.db)
```bash
scp root@<your_ip>:/opt/crypto_bot/trades.db ./trades.db
```

### Upload Updated Code
```bash
# From your local machine
scp -r crypto_bot root@<your_ip>:/opt/
```

---

## 🐛 Troubleshooting

### Bot won't start?
```bash
# Check error logs
sudo journalctl -u crypto-bot -n 100

# Try running manually to see the error
cd /opt/crypto_bot
source venv/bin/activate
python app.py
```

### Can't access dashboard?
```bash
# Check if Flask is listening
sudo netstat -tlnp | grep 8080

# If not, check service status
sudo systemctl status crypto-bot
```

### API Key issues?
```bash
# Verify .env file is readable
cat /opt/crypto_bot/.env

# Make sure Binance API key is enabled
# (Go to https://testnet.binance.vision/)
```

### Out of disk space?
```bash
# Check disk usage
df -h

# Clear old logs if needed
sudo journalctl --vacuum=50M
```

---

## 📊 Monitoring

### CPU/Memory Usage
```bash
# SSH into droplet and run
top
# Press 'q' to exit
```

### Check Bot Process
```bash
ps aux | grep python
```

### Network Connectivity
```bash
# Test connection to Binance
curl -I https://testnet.binance.vision

# Check droplet uptime
uptime
```

---

## 🔐 Security Tips

1. **Never commit `.env` to git** — it's already in .gitignore
2. **Use Testnet first** — `USE_TESTNET = True` in config.py
3. **Limit API key permissions** on Binance dashboard
4. **Disable withdrawals** on your Binance API key
5. **Enable 2FA** on your Binance account
6. **Keep droplet updated**: `apt update && apt upgrade -y`

---

## 💰 Costs

| Service | Cost | Notes |
|---------|------|-------|
| DigitalOcean Droplet | $6/month | 1GB RAM, 1 vCPU (more than enough) |
| Bandwidth | Free | 1 TB/month included |
| Monitoring | Free | Optional |
| **Total** | ~$6/month | Runs 24/7 continuously |

---

## 📞 Support

If the bot crashes:
- Systemd auto-restarts it after 10 seconds
- Check logs: `sudo journalctl -u crypto-bot -f`
- Restart manually: `sudo systemctl restart crypto-bot`

Your bot will run **24/7 without needing your local machine on**.
