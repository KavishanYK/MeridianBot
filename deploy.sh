#!/bin/bash
set -e

echo "🤖 Crypto Trading Bot – Auto-Deploy Script"
echo "=========================================="

# Step 1: Update system
echo "📦 Updating system..."
apt update && apt upgrade -y

# Step 2: Install dependencies
echo "📦 Installing Python and dependencies..."
apt install -y python3 python3-pip python3-venv git curl wget

# Step 3: Clone repo (if not already present)
if [ ! -d "/opt/crypto_bot" ]; then
    echo "📂 Cloning repository..."
    git clone https://github.com/yourusername/crypto_bot.git /opt/crypto_bot
else
    echo "✅ /opt/crypto_bot already exists, skipping clone"
fi

cd /opt/crypto_bot

# Step 4: Create venv and install requirements
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Step 5: Create .env file (user must fill in API keys)
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
    cat > .env << 'EOF'
BINANCE_API_KEY=paste_your_testnet_api_key_here
BINANCE_API_SECRET=paste_your_testnet_api_secret_here
EOF
    echo "⚠️  EDIT .env and add your Binance API keys before starting!"
fi

# Step 6: Copy systemd service file
echo "⚙️  Installing systemd service..."
cp crypto-bot.service /etc/systemd/system/
systemctl daemon-reload

# Step 7: Enable service
echo "🚀 Enabling crypto-bot service..."
systemctl enable crypto-bot

# Step 8: Start service
echo "▶️  Starting crypto-bot..."
systemctl start crypto-bot

# Step 9: Status check
echo ""
echo "✅ Deployment complete!"
echo ""
systemctl status crypto-bot

echo ""
echo "📖 Next steps:"
echo "  1. Edit /opt/crypto_bot/.env with your Binance API keys"
echo "  2. Restart the service: sudo systemctl restart crypto-bot"
echo "  3. View logs: sudo journalctl -u crypto-bot -f"
echo "  4. Access dashboard: http://<your_server_ip>:8080"
echo ""
