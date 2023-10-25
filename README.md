# Gradio Share Server (FRP)

This repo is a fork of the [Fast Reverse Proxy (FRP)](https://github.com/fatedier/frp) implementation that is running on Gradio's Share servers to enable Gradio's [Share links](https://www.gradio.app/guides/sharing-your-app#sharing-demos).

## Background

When you create a Gradio app and launch it with `share=True` like this:

```py
import gradio as gr

app = gr.Interface(lambda x: x, "image", "image")
app.launch(share=True)
```

you get a share link that looks

Your Gradio app runs locally, but we use FRP allows you to expose a local server located behind a NAT or firewall to the Internet

We've open-sourced it so that you can run your own Share Servers, allowing


