# Gradio Share Server (FRP)

This repo is a fork of [Fast Reverse Proxy (FRP)](https://github.com/fatedier/frp), which runs on Gradio's Share Server to enable Gradio's [Share links](https://www.gradio.app/guides/sharing-your-app#sharing-demos). Instructions on how to set up your own Share Server and thereby generate custom share links are below 🔥

## Background

When you create a Gradio app and launch it with `share=True` like this:

```py
import gradio as gr

app = gr.Interface(lambda x: x, "image", "image")
app.launch(share=True)
```

you get a share link like: `https://07ff8706ab.gradio.live`, and your Gradio app is now accessible to anyone through the Internet (for up to 72 hours).

**How does this happen?** Your Gradio app runs on a Python server locally, but we use FRP to expose the local server to the Internet. FRP consists of two parts:
* FRP Client: this runs on *your* machine. We package binaries for the most common operating systems, and the [FRP Client for your system is downloaded](https://github.com/gradio-app/gradio/blob/main/gradio/tunneling.py#L47) the first time you create a share link on your machine.
* FRP Server: this runs on Gradio's Share Server, but since the FRP Server is open-source, you can run it on your own server as well! 

## Why Run Your Own Share Server?

You might want to run your own server for several reasons:
* Custom domains: Instead of `*.gradio.live`, you can use any domain your heart desires as long as you own it
* Longer links: when you run your own Share Server, you don't need to restrict share links from expiring after 72 hours
* Security / privacy: by setting up your own Share Server in your virtual private cloud, you can make your information security team happy

Its also quite straightforward. In your Gradio app, the only change you'll make is passing in the IP address to your share server, as the `share_server_address` parameter in `launch()`:

```py
import gradio as gr

app = gr.Interface(lambda x: x, "image", "image")
app.launch(share=True, share_server_address="44.237.78.176:7000")
```

And voila!

```
Running on your Share Server: https://07f56cd0f87061c8a1.yourorganization.com
```

## Setting Up A Share Server

### Prerequisites

* A **server** (e.g. EC2 machine on AWS) that is running Linux and connected to the Internet. Most servers provided by cloud providers (e.g. a `t2-small` on AWS) should do just fine, we recommend having at least 2 GB of RAM and 8 GB of disk space. You will need to be able to SSH into your server.
* The server should have an **elastic IP address** and a **domain name**. The specific instructions depend on the domain name registrar and cloud provider you use. For example, here are the instructions for [AWS using EC2 and Route53](https://medium.com/front-end-weekly/connecting-a-domain-to-an-aws-ec2-instance-using-route53-69faffddda39).

**Important**: not just the root domain, but all subdomains should route to the IP address of your server. This typically means that you should have a wildcard entry in your DNS records, like the bottom-most entry here: 

<img width="1354" alt="image" src="https://github.com/huggingface/frp/assets/1778297/3b2335bc-3422-4d4f-b0ea-c84b93cc0d07">


### 1. Install Docker (v. 20.10 or higher)

You can do this by running these commands (for this guide, we assume you are running Ubuntu) sequentially in the terminal after you have SSH'd into the server:

```console
sudo apt update
```
```console
sudo apt install apt-transport-https ca-certificates curl software-properties-common
```
```console
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
```
```console
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
```
```console
apt-cache policy docker-ce
```
```console
sudo apt install docker-ce
```

Confirm that you Docker has been installed and you are running version `20.10` or higher by running: `docker version` in the terminal. You should see something like:

```
Client: Docker Engine - Community
 Version:           24.0.6
...
```

### 2. Clone This Repo

```console
git clone git@github.com:huggingface/frp.git
```

```console
cd frp
```

Note for advanced users: If you would like to change [which port FRPS runs on](https://github.com/huggingface/frp/tree/b0d5567f5df2bfc12a56bc8d787d23e2668ed9af/conf) (default is 7000) or the [expiry time of share links](https://github.com/huggingface/frp/blob/b0d5567f5df2bfc12a56bc8d787d23e2668ed9af/server/control.go#L213) (default is 72 hours), edit the linked files directly on your server.

### 3. Edit the FRP Server Configuration File

Open the `scripts/frps.ini` file, and edit the value of the `subdomain_host` property to reflect your domain (without any prefixes). 

You can also set `bind_port`, which is the default port used to the FRP connections to something other than `7000`, or customize the 404 page (`custom_404_page`) which is shown when there is no active Gradio app connected to the Share Server.

Here's a sample customized `.ini` file:

```ini
[common]
log_level = trace
tcp_mux = true
bind_port = 7000
dashboard_port = 7001
vhost_http_port = 80
subdomain_host = my-gpt-wrapper.com
detailed_errors_to_client = false
custom_404_page = /etc/frp/my-404.html
```

### 4. Launch the FRP Server Docker Container

Note: you may need `sudo` permissions for these commands:

```console
docker build -f dockerfiles/Dockerfile-for-frps -t frps:0.2 .
```

```console
docker run --log-opt max-size=100m --memory=1G --cpus=1 --name frps3 -d --restart unless-stopped --network host -v ~/frp/scripts:/etc/frp frps:0.2 -c /etc/frp/frps.ini
```

### 4. Open Ports on Your Server

In order to 

That's it! You now have your own little Share Server! As mentioned earlier, you can use it by passing the IP address and FRPS port as the `share_server_address` parameter in `launch()` like this:

```py
import gradio as gr

app = gr.Interface(lambda x: x, "image", "image")
app.launch(share=True, share_server_address="44.237.78.176:7000")
```

**Note**: If you have installed HTTPS certificates on your Share Server, and your share links are being served through HTTPS, then you should also set `share_server_protocol="https"` in `launch()`.

