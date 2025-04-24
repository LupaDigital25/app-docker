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

## deploy

# 1. Clone repo metadata only (no files yet)
rm -rf ~/app-docker
git clone --filter=blob:none --no-checkout https://github.com/LupaDigital25/app-docker.git
cd app-docker

# 2. Enable sparse checkout
git sparse-checkout init --cone

# 3. Tell Git to only check out the deploy folder
git sparse-checkout set deploy

# shake git
git checkout main

# 4. Move into the deploy folder
cd deploy


###

docker-compose up -d
docker-compose run --rm certbot
docker restart nginx
