# app-docker

if you want to run the app locally, you can use the docker image `hugoverissimo21/lupa-digital-25:latest` or build it from the repo.

```bash
docker pull hugoverissimo21/lupa-digital-25:latest

docker run -d \
    --cpus="8" \                # docker: Limit to 8 CPU threads
    --memory="16g" \            # docker: Limit container to 16 GB RAM
    --memory-swap="16g" \       # docker: Disable swap overcommit
    -e SPARK_CORES="4" \        # spark: Spark will use 4 threads internally
    -e SPARK_MEM="4g" \         # spark: Spark driver + executor memory = 4 GB
    -p 80:5000 \                # Public HTTP port -> Flask port
    hugoverissimo21/lupa-digital-25:latest
```

in order to deploy the whole setup for production, you can use the docker-compose file in the `deploy` folder. This will create a nginx server with https support and a flask app running redirecting to external services.

- clone the deply folder from the repo
```bash
git clone --filter=blob:none --no-checkout https://github.com/LupaDigital25/app-docker.git
cd app-docker
git sparse-checkout init --cone
git sparse-checkout set deploy
git checkout main
```

- run the docker compose
```bash
cd deploy
docker-compose pull
docker-compose up -d
docker-compose run --rm certbot
docker compose exec nginx nginx -s reload
```

---

useful commands:

```bash
docker-compose down
rm -rf ~/app-docker
docker system prune -af

docker ps

docker run -it --entrypoint bash hugoverissimo21/lupa-digital-25
```