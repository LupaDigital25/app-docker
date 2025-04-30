# Lupa Digital 25 – Dockerized Deployment

This repository contains the Docker-based deployment configuration for the Lupa Digital Flask web application. It includes a `docker-compose.yml` file and associated configuration files needed to launch the application and its dependencies in a containerized environment. Designed for portability and ease of deployment, this setup allows seamless integration with Spark and supports production-ready hosting on platforms like DigitalOcean.

It also creates a Docker image for the app, which can be used to run the application locally or in production. The image is built using a Dockerfile and includes all necessary dependencies and configurations.

## Project Structure

```bash
app-docker/
│
├── .github/workflows/              # Create Docker image at each commit
|
├── app/                            # Main application code
│   ├── app.py                      # Main Flask application
│   ├── ...                         # Other application files (e.g., static, templates)
|
├── data/news_processed/            # Processed data files
│
├── deploy/
│   ├── docker-compose.yml          # Docker Compose configuration
│   ├── deploy.sh                   # Deployment script
│   ├── nginx/                      # Nginx configuration files
│
├── Dockerfile                      # Dockerfile for building the app image
├── requirements.txt                # Python dependencies for the app
└── ...                             # Other files (e.g., README, LICENSE)
```


## Deployment Guide

This guide provides instructions for running the app locally using Docker or deploying it to production with HTTPS support via Nginx and Docker Compose.

### Locally with Docker

1. Pull the Docker image
```bash
docker pull hugoverissimo21/lupa-digital-25:latest
```

2. Run the container
```bash
docker run -d \
    --cpus="8" \                # docker: Limit to 8 CPU threads
    --memory="16g" \            # docker: Limit container to 16 GB RAM
    --memory-swap="16g" \       # docker: Disable swap overcommit
    -e SPARK_CORES="4" \        # spark: Spark will use 4 threads internally
    -e SPARK_MEM="4g" \         # spark: Spark driver + executor memory = 4 GB
    -p 80:5000 \                # Public HTTP port -> Flask port
    hugoverissimo21/lupa-digital-25:latest
```

After this, the app will be available at `http://localhost`.

### Production Deployment with HTTPS

This method sets up an Nginx reverse proxy with HTTPS support and the Flask app behind it.

1. Clone only the `deploy` folder
```bash
git clone --filter=blob:none --no-checkout https://github.com/LupaDigital25/app-docker.git
cd app-docker
git sparse-checkout init --cone
git sparse-checkout set deploy
git checkout main
```

2. Deploy with Docker Compose
```bash
cd deploy
chmod +x ./deploy.sh
./deploy.sh
```

This will:
- Set up Nginx with HTTPS (via Let's Encrypt)
- Run the Flask + Spark application
- Automatically redirect HTTP to HTTPS


## Useful Commands

Check running containers:

```bash
docker ps
```

Clean up Docker and temporary files:

```bash
docker-compose down             # Stop and remove containers
rm -rf ~/app-docker             # Remove local repo clone
docker system prune -af         # Clean up Docker
```

Access the container for debugging:

```bash
docker run -it --entrypoint bash hugoverissimo21/lupa-digital-25
```