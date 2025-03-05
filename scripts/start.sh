#!/bin/bash

# stop and remove existing frps3 container if it exists and then start a new one

if docker ps -a | grep -q frps3; then
    echo "Stopping and removing existing frps3 container..."
    sudo docker stop frps3
    sudo docker rm frps3
fi

# Install requirements for the connection logger server
echo "Checking and installing Python requirements..."
cd /home/ubuntu/frp
pip install -r /home/ubuntu/frp/scripts/requirements.txt

# Start the connection logger server if it's not already running
if ! pgrep -f "connection_logger_server.py" > /dev/null; then
    echo "Starting connection logger server..."
    
    # Set the environment variable for the database path
    export GRADIO_DB_PATH="/home/ubuntu/frp/gradio_connections.db"
    
    # Start the server with the environment variable
    nohup env GRADIO_DB_PATH="$GRADIO_DB_PATH" python /home/ubuntu/frp/scripts/connection_logger_server.py > /home/ubuntu/frp/connection_logger.log 2>&1 &
    
    # Wait a moment to ensure the server starts
    sleep 2
    
    # Check if the server started successfully
    if ! curl -s http://127.0.0.1:8000/health > /dev/null; then
        echo "Warning: Connection logger server failed to start. Continuing anyway..."
    else
        echo "Connection logger server started successfully."
    fi
fi

sudo docker run --log-opt max-size=100m --memory=28G --cpus=6 --name frps3 -d --restart unless-stopped --network host -v ~/frp/combined:/etc/frp frps:0.2 -c /etc/frp/frps_tls.ini

# renew tls certificate every 2 months

CRON_SCHEDULE="0 0 1 */2 *" 
COMMAND="/home/ubuntu/frp/scripts/renew_tls_certificate.sh"
IDENTIFIER="# renew_tls_certificate"

CRON_JOB="$CRON_SCHEDULE $COMMAND $IDENTIFIER"
EXISTING_CRONS=$(sudo crontab -l 2>/dev/null || true)

if echo "$EXISTING_CRONS" | grep -q "$IDENTIFIER"; then
  UPDATED_CRONS=$(echo "$EXISTING_CRONS" | sed "/$IDENTIFIER/d")
  echo -e "$UPDATED_CRONS\n$CRON_JOB" | sudo crontab -
else
  echo -e "$EXISTING_CRONS\n$CRON_JOB" | sudo crontab -
fi

echo "Cron job successfully managed!"
