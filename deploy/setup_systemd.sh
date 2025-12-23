#!/bin/bash
# Setup systemd service for auto-start

set -e

echo "====================================="
echo "Configuring systemd service"
echo "====================================="

# Create log directory
sudo mkdir -p /var/log/docmanagement
sudo chown -R ubuntu:ubuntu /var/log/docmanagement

# Copy service file
sudo cp /var/www/docmanagement/deploy/docmanagement.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable docmanagement
sudo systemctl start docmanagement

# Check status
sudo systemctl status docmanagement

echo "====================================="
echo "Service configured!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status docmanagement    - Check status"
echo "  sudo systemctl restart docmanagement   - Restart service"
echo "  sudo systemctl stop docmanagement      - Stop service"
echo "  sudo journalctl -u docmanagement -f    - View logs"
echo "====================================="
