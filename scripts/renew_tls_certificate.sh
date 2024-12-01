if docker ps -a | grep -q frps3; then
    echo "Stopping and removing existing frps3 container..."
    sudo docker stop frps3
    sudo docker rm frps3
fi

sudo certbot renew

sudo cp /etc/letsencrypt/live/gradio-live.com/fullchain.pem ~/frp/combined
sudo cp /etc/letsencrypt/live/gradio-live.com/privkey.pem ~/frp/combined

sudo docker run --log-opt max-size=100m --memory=28G --cpus=6 --name frps3 -d --restart unless-stopped --network host -v ~/frp/combined:/etc/frp frps:0.2 -c /etc/frp/frps_tls.ini
