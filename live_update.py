# live_update.py
from flask import Flask
from flask_socketio import SocketIO

socketio = None

## We need this separate file to avoid circular imports

def create_app():
    global socketio
    app = Flask(__name__)
    socketio = SocketIO(app)
    # Additional configuration and blueprint registration goes here
    return app