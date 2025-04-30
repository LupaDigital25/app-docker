#!/bin/bash

set -e

CERT_PATH="./certbot/conf/live/lupa-digital.pt/fullchain.pem"
NGINX_DIR="./nginx"

echo "Checking if certificate exists..."

if [ ! -f "$CERT_PATH" ]; then
  echo "Certificate not found."
  echo "Using HTTP-only config for initial ACME challenge..."
  cp "$NGINX_DIR/nginx.http.conf" "$NGINX_DIR/nginx.conf"

  docker-compose up -d nginx
  echo "Waiting for Nginx to start..."
  sleep 5

  echo "Running Certbot to issue HTTPS certificate..."
  docker-compose run --rm certbot

  echo "Stopping temporary Nginx instance..."
  docker-compose down
else
  echo "Certificate already exists."
fi

echo "Switching to full HTTPS config..."
cp "$NGINX_DIR/nginx.full.conf" "$NGINX_DIR/nginx.conf"

echo "Starting full application stack..."
docker-compose up -d

echo "Deployment complete. HTTPS should now be active."
