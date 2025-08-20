
import gradio as gr
from app import Me

# Create instance and deploy
me = Me()
gr.ChatInterface(me.chat, type="messages").launch()