docker run --name frps -d --restart unless-stopped --network host -v ~/frp/scripts:/etc/frp frps -c /etc/frp/frps.ini
