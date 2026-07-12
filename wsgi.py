"""
IBM Cloud Foundry / IBM Code Engine deployment entry point.
Gunicorn WSGI config for Travel Planner Agent.
"""
import os
from app import create_app

application = create_app(os.getenv("FLASK_ENV", "production"))

if __name__ == "__main__":
    application.run()
