# app-docker

#### pull:

```bash
docker pull hugoverissimo21/lupa-digital-25:latest
```

#### run:

```bash
docker ps
docker stop ca1b76df4df4
docker rm ca1b76df4df4
```

- local
```bash
docker run -p 6969:5000 hugoverissimo21/lupa-digital-25:latest
```

- current digital ocean server
```bash
docker run -d -e SPARK_CORES="*" -e SPARK_MEM="6g" -p 80:5000 hugoverissimo21/lupa-digital-25:latest
```

- server (with limitations example)
```bash
docker run -d \
  --cpus="8" \                # docker: Limit to 8 CPU threads
  --memory="16g" \            # docker: Limit container to 16 GB RAM
  --memory-swap="16g" \       # docker: Disable swap overcommit
  -e SPARK_CORES="4" \        # spark: Spark will use 4 threads internally
  -e SPARK_MEM="4g" \         # spark: Spark driver + executor memory = 4 GB
  -p 80:5000 \                # Public HTTP port → Flask port
  hugoverissimo21/lupa-digital-25
```

#### debug:

```bash
docker run -it --entrypoint bash hugoverissimo21/lupa-digital-25
```

#### deploy using https (to be finished):

- remove the old deploy folder and stuff
```bash
docker-compose down
rm -rf ~/app-docker
docker system prune -af
```

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
docker restart nginx
```
