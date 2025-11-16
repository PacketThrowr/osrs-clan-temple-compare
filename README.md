# Clan/Temple Comparison Webhook
A FastAPI service that automatically syncs your Old School RuneScape clan roster with TempleOSRS and tracks member promotions based on time in clan. Integrates with the RuneLite "Clan Exports" plugin to receive clan data and posts results to Discord.
How It Works
App.py Overview
The FastAPI application performs three main functions:

Member Comparison: Compares your in-game clan roster (received from RuneLite's Clan Exports plugin) against your TempleOSRS group members to identify:

Members in clan but not on Temple
Members on Temple but not in clan


Promotion Tracking: Automatically calculates which members are eligible for rank promotions based on time in clan:
This is our current requirements, these can be changed by adjusting the logic in app.py

0-3 months: Squire
3-6 months: Striker
6-9 months: Inquisitor
9-12 months: Expert
12+ months: Knight


Discord Notifications: Posts a formatted summary to your Discord channel with all sync results and promotion recommendations.

Workflow:

RuneLite Clan Exports plugin sends POST request with clan roster
App fetches latest TempleOSRS member list
Compares rosters using normalized names (handles spaces, underscores, hyphens)
Calculates promotion eligibility based on join dates
Posts results to Discord webhook

Installation
Prerequisites
bash# Install Python dependencies
pip install fastapi pydantic requests

# Install Uvicorn (ASGI server)
pip install uvicorn
Required Files
Place these files in your working directory (e.g., /data):

app.py - Main FastAPI application
get_temple_members.py - Script to fetch Temple members
clan-webhook.service - Systemd service file (example)

Configuration
1. Get Your TempleOSRS Group URL

Go to TempleOSRS
Navigate to your clan/group page
Copy the group ID from the URL (e.g., https://templeosrs.com/groups/overview.php?id=1234)
Your API URL will be: https://templeosrs.com/api/groupmembers.php?id=1234

2. Set Up Discord Webhook

Open Discord and go to your server
Right-click the channel where you want notifications → Edit Channel
Go to Integrations → Webhooks → New Webhook
Customize the name/avatar if desired
Click Copy Webhook URL
Save this URL for the service configuration

3. Configure the Systemd Service
Edit clan-webhook.service and update these fields:
ini[Service]
User=YOUR_USERNAME          # Replace with your Linux username
Group=YOUR_GROUP            # Replace with your Linux group (usually same as username)
WorkingDirectory=/data       # Update if using different directory

# Replace with your actual URLs:
Environment="DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
Environment="TEMPLE_API_URL=https://templeosrs.com/api/groupmembers.php?id=YOUR_GROUP_ID"

4. Install and Enable the Service
bash# Copy service file to systemd directory
sudo cp clan-webhook.service /etc/systemd/system/

# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable clan-webhook

# Start the service
sudo systemctl start clan-webhook

# Check status
sudo systemctl status clan-webhook
5. Port Forwarding (Router Configuration)
To allow RuneLite to send data to your server:

Find your server's local IP address: ip addr or hostname -I
Access your router's admin panel (usually 192.168.1.1 or 192.168.0.1)
Navigate to Port Forwarding settings (location varies by router)
Create a new port forwarding rule:

External Port: 8000 (or your preferred port)
Internal Port: 8000
Internal IP: Your server's local IP
Protocol: TCP


Save and apply changes

Note: You'll also need your public IP address for the RuneLite plugin configuration. Find it at whatismyip.com
6. Configure RuneLite Clan Exports Plugin

Open RuneLite
Install the "Clan Exports" plugin if not already installed
Configure the plugin with:

Enable 'Send export to a URL'
Webhook URL: http://YOUR_PUBLIC_IP:8000/compare-clan


# Testing
Send a test request to verify everything works:
bashcurl -X POST http://localhost:8000/compare-clan \
  -H "Content-Type: application/json" \
  -d '{
    "clanName": "Test Clan",
    "clanMemberMaps": [
      {
        "rsn": "Player1",
        "rank": "Squire",
        "joinedDate": "01-Jan-2024"
      }
    ]
  }'
You should see results in your Discord channel!

# Troubleshooting
Service won't start:
bash# View detailed logs
sudo journalctl -u clan-webhook -f
Can't connect from RuneLite:

Verify port forwarding is configured correctly
Check firewall rules: sudo ufw allow 8000/tcp
Confirm service is running: sudo systemctl status clan-webhook

Discord messages not appearing:

Verify webhook URL is correct
Check webhook permissions in Discord
