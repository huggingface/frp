#!/bin/bash

# stop and remove existing frps3 container if it exists and then start a new one

if docker ps -a | grep -q frps3; then
    echo "Stopping and removing existing frps3 container..."
    sudo docker stop frps3
    sudo docker rm frps3
fi

sudo docker run --log-opt max-size=100m --memory=28G --cpus=6 --name frps3 -d --restart unless-stopped --network host -v ~/frp/combined:/etc/frp frps:0.2 -c /etc/frp/frps_tls.ini

# renew tls certificate every 2 months

CRON_SCHEDULE="0 0 1 */2 *" 
COMMAND="/home/ubuntu/frp/scripts/renew_tls_certificate.sh"
IDENTIFIER="# renew_tls_certificate"

CRON_JOB="$CRON_SCHEDULE $COMMAND $IDENTIFIER"
EXISTING_CRONS=$(crontab -l 2>/dev/null || true)

if echo "$EXISTING_CRONS" | grep -q "$IDENTIFIER"; then
  UPDATED_CRONS=$(echo "$EXISTING_CRONS" | sed "/$IDENTIFIER/d")
  echo -e "$UPDATED_CRONS\n$CRON_JOB" | crontab -
else
  echo -e "$EXISTING_CRONS\n$CRON_JOB" | crontab -
fi

echo "Cron job successfully managed!"
