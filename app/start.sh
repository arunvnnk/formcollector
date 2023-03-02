#!/bin/sh
cd $APP_HOME
if [ ! -f "./cert.pem" ]; then
  echo "Generating SSL Certificate"
  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes -subj "/CN=servehtml"
else
  echo "Certificate Exists"
fi
gunicorn --certfile ./cert.pem --keyfile ./key.pem --bind $APP_LISTEN:$APP_PORT app:app