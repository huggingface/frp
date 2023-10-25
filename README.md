# Gradio Share Server (FRP)

This repo is a fork of the [Fast Reverse Proxy (FRP)](https://github.com/fatedier/frp) implementation that is running on Gradio's Share Server to enable Gradio's [Share links](https://www.gradio.app/guides/sharing-your-app#sharing-demos).

## Background

When you create a Gradio app and launch it with `share=True` like this:

```py
import gradio as gr

app = gr.Interface(lambda x: x, "image", "image")
app.launch(share=True)
```

you get a share link like: `https://07ff8706ab.gradio.live`, and your Gradio app is now accessible to anyone through the Internet (for up to 72 hours).

**How does this happen?** Your Gradio app runs on a Python server locally, but we use FRP to expose the local server to the Internet. FRP consists of two parts:
* FRP Client: this runs on *your* machine. We package binaries for the most common operating systems, and the [FRP Client for your system is downloaded](https://github.com/gradio-app/gradio/blob/main/gradio/tunneling.py#L47) the first time you create a share link on your machine)
* FRP Server: this runs on Gradio's Share Server, and keep reading to see how you can run it on your own server as well! 

## 

## 

We've open-sourced it so that you can run your own Share Servers, allowing


