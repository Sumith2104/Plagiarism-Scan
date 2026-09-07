#!/usr/bin/env bash
# ==============================================================================
# PlagiaScan AWS EC2 1-Click Deployment Script with sslip.io Automatic HTTPS
# ==============================================================================

set -e

echo "======================================================"
echo "   PlagiaScan - Automated AWS EC2 Deployment Setup    "
echo "======================================================"

# 1. Set up swap space if system has <= 2GB RAM (vital for AWS t2.micro 1GB RAM)
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM_MB" -lt 2500 ] && [ ! -f /swapfile ]; then
    echo "[*] Adding 2GB swap space to prevent out-of-memory errors on t2.micro..."
    sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab > /dev/null
    echo "[+] Swap configured successfully."
fi

# 2. Ensure Docker & Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "[-] Installing Docker..."
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker $USER || true
    echo "[+] Docker installed successfully."
fi

# 2. Automatically retrieve EC2 Public IP address
echo "[*] Detecting Public IP Address..."
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)
PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)

if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s https://ifconfig.me || curl -s https://icanhazip.com || true)
fi

if [ -z "$PUBLIC_IP" ]; then
    read -p "Could not auto-detect public IP. Please enter your AWS Public IP: " PUBLIC_IP
fi

DOMAIN="${PUBLIC_IP}.sslip.io"
echo "[+] Detected Public IP: $PUBLIC_IP"
echo "[+] Target Domain:      $DOMAIN"

# 3. Create or update .env file
if [ ! -f .env ]; then
    echo "[*] Creating .env file..."
    cat <<EOF > .env
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "plagiascan-production-secret-key-12345")
QDRANT_URL=local
DATABASE_URL=sqlite:///./plagiascan.db
DOMAIN=$DOMAIN
EOF
else
    # Update or append DOMAIN
    if grep -q "^DOMAIN=" .env; then
        sed -i "s/^DOMAIN=.*/DOMAIN=$DOMAIN/" .env
    else
        echo "DOMAIN=$DOMAIN" >> .env
    fi
fi

export DOMAIN

# 4. Build and start containers
echo "[*] Building and launching PlagiaScan unified containers..."
sudo docker compose -f docker-compose.prod.yml down --remove-orphans || true
sudo docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "======================================================"
echo "  🎉 Deployment Complete! PlagiaScan is now LIVE!    "
echo "======================================================"
echo ""
echo "  👉 Public URL (Secure HTTPS):"
echo "     https://$DOMAIN"
echo ""
echo "  👉 Fallback Direct Port:"
echo "     http://$DOMAIN:8000"
echo ""
echo "  NOTE: In your AWS EC2 Security Group, make sure you"
echo "  have added Inbound Rules for:"
echo "    - Port 80   (HTTP)"
echo "    - Port 443  (HTTPS)"
echo "    - Port 8000 (Custom TCP - optional fallback)"
echo "======================================================"
