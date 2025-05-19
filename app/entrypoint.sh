#!/bin/sh
# Run database migrations
flask --app terracore db upgrade
# Start Gunicorn
exec gunicorn -c gunicorn.conf.py "terracore:create_app()"