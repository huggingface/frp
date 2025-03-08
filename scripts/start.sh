#!/bin/bash

# Parse command line arguments
RESTART_LOGGER_ONLY=false
if [[ "$1" == "--logger" ]]; then
    RESTART_LOGGER_ONLY=true
    echo "Restarting only the connection logger server..."
fi

if [[ "$RESTART_LOGGER_ONLY" == "false" ]]; then
    # stop and remove existing frps3 container if it exists and then start a new one
    if docker ps -a | grep -q frps3; then
        echo "Stopping and removing existing frps3 container..."
        sudo docker stop frps3
        sudo docker rm frps3
    fi
fi

# Kill any process running on port 8765
echo "Checking for processes on port 8765..."
PORT_PID=$(lsof -ti:8765)
if [ ! -z "$PORT_PID" ]; then
    echo "Killing process $PORT_PID running on port 8765..."
    kill -9 $PORT_PID
fi

# Install requirements for the connection logger server
echo "Checking and installing Python requirements..."
cd /home/ubuntu/frp
pip install -r /home/ubuntu/frp/scripts/requirements.txt

# Set the environment variable for the database path
export GRADIO_DB_PATH="/home/ubuntu/frp/gradio_connections.db"

# Start the connection logger server
echo "Starting connection logger server..."
nohup python /home/ubuntu/frp/scripts/connection_logger_server.py > /home/ubuntu/frp/connection_logger.log 2>&1 &

# Wait a moment to ensure the server starts
sleep 2

# Check if the server started successfully
if ! curl -s http://127.0.0.1:8765/health > /dev/null; then
    echo "Warning: Connection logger server failed to start."
else
    echo "Connection logger server started successfully."
fi

if [[ "$RESTART_LOGGER_ONLY" == "false" ]]; then
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
fi
