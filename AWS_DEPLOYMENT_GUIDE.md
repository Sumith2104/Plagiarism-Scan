# 🚀 Hosting PlagiaScan on AWS with sslip.io (24/7 Access)

This guide walks you step-by-step through deploying PlagiaScan to an **AWS EC2 Virtual Machine (Free Tier eligible)** so that your friend and anyone in the world can access it **24/7**, even when your personal computer is turned off.

---

## 🌟 Why AWS + sslip.io?

- **24/7 Cloud Hosting**: Runs on Amazon's cloud data centers.
- **Zero DNS Setup**: `sslip.io` automatically maps your AWS Public IP to a real domain name (e.g. `54.210.35.120.sslip.io`).
- **Free Automatic HTTPS/SSL**: Caddy automatically provisions real Let's Encrypt certificates for your `sslip.io` domain.
- **Free Tier Eligible**: Uses standard AWS EC2 (free for 12 months on `t2.micro`).

---

## Step 1: Launch an AWS EC2 Instance

1. Log into your [AWS Management Console](https://console.aws.amazon.com/).
2. In the top search bar, search for **EC2** and click on **EC2**.
3. Click the orange **"Launch instance"** button.
4. Configure the instance settings:
   - **Name**: `plagiascan-server`
   - **Application and OS Images (AMI)**: Select **Ubuntu** (choose **Ubuntu Server 24.04 LTS** or **22.04 LTS**, 64-bit x86).
   - **Instance type**: Select **`t2.micro`** (Free Tier eligible) or **`t3.small`**.
   - **Key pair**:
     - If you have an existing key pair, select it.
     - If not, you can create one or select *"Proceed without a key pair"* (we will use **EC2 Instance Connect** in the browser).
5. **Network Settings** (Very Important):
   - Click **Edit** on Network Settings.
   - Check the following checkboxes:
     - ✅ **Allow SSH traffic from Anywhere (`0.0.0.0/0`)**
     - ✅ **Allow HTTP traffic from the internet (`0.0.0.0/0`)** — Port 80
     - ✅ **Allow HTTPS traffic from the internet (`0.0.0.0/0`)** — Port 443
   - Click **Add security group rule**:
     - Type: **Custom TCP**
     - Port range: `8000`
     - Source: `Anywhere` (`0.0.0.0/0`)
6. **Configure Storage**:
   - Change the storage from `8 GiB` to **`15 GiB` or `20 GiB` gp3** (AWS Free Tier includes up to 30 GB free storage).
7. Click **"Launch instance"** at the bottom right.

---

## Step 2: Connect to Your AWS Server

1. Go back to the **Instances** list in your EC2 Console.
2. Click on your newly launched instance.
3. Click the **"Connect"** button at the top.
4. Select the **"EC2 Instance Connect"** tab and click **"Connect"**.
5. A terminal window will open directly in your web browser!

---

## Step 3: Run the 1-Click Deployment Script

Copy and paste the following commands into the EC2 browser terminal:

```bash
# 1. Clone the repository
git clone https://github.com/Sumith2104/Plagiarism-Scan.git
cd Plagiarism-Scan

# 2. Run the automated deployment script
bash deploy_aws.sh
```

### What `deploy_aws.sh` Does Automatically:
1. Allocates **2GB swap space** so memory-intensive ML models and builds never crash on `t2.micro`.
2. Installs Docker and Docker Compose.
3. Automatically detects the server's **AWS Public IP**.
4. Configures the `sslip.io` domain (e.g. `54.210.35.120.sslip.io`).
5. Builds and launches the unified PlagiaScan container and Caddy reverse proxy.
6. Automatically secures the domain with **HTTPS/TLS**.

---

## Step 4: Share with Your Friend!

Once the script completes, it will print your live URLs:

```
======================================================
  🎉 Deployment Complete! PlagiaScan is now LIVE!    
======================================================

  👉 Public URL (Secure HTTPS):
     https://<YOUR-AWS-IP>.sslip.io

  👉 Fallback Direct Port:
     http://<YOUR-AWS-IP>.sslip.io:8000
======================================================
```

Send the **`https://<YOUR-AWS-IP>.sslip.io`** link to your friend. They can open it in any web browser and start scanning documents immediately!

---

## 🛠 Useful Commands on the Server

- **View live server logs:**
  ```bash
  sudo docker compose -f docker-compose.prod.yml logs -f app
  ```
- **Restart the application:**
  ```bash
  sudo docker compose -f docker-compose.prod.yml restart
  ```
- **Stop the application:**
  ```bash
  sudo docker compose -f docker-compose.prod.yml down
  ```
- **Update with latest code from GitHub:**
  ```bash
  git pull
  bash deploy_aws.sh
  ```
