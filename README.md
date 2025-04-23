# app-docker

#### run:

- local
```bash
docker pull hugoverissimo21/lupa-digital-25:latest

docker run -p 6969:5000 hugoverissimo21/lupa-digital-25:latest
```

- current digital ocean server
```bash
docker pull hugoverissimo21/lupa-digital-25:latest
docker run
  -e SPARK_CORES="*" \
  -e SPARK_MEM="6g" \
  -p 80:5000 \
  hugoverissimo21/lupa-digital-25
```

- server (with limitations example)

```bash
docker run -d \
  --cpus="8" \                # docker: Limit to 8 CPU threads
  --memory="16g" \            # docker: Limit container to 16 GB RAM
  --memory-swap="16g" \       # docker: Disable swap overcommit
  -e SPARK_CORES="4" \          # spark: Spark will use 4 threads internally
  -e SPARK_MEM="4g" \           # spark: Spark driver + executor memory = 4 GB
  -p 80:5000 \                # Public HTTP port → Flask port
  hugoverissimo21/lupa-digital-25
```

#### debug:

```bash
docker run -it --entrypoint bash hugoverissimo21/lupa-digital-25
```
